"""
Rerank 微服务（组长端口表：127.0.0.1:8002）

启动（在 backend 目录）：
  uvicorn rerank_service.main:app --host 127.0.0.1 --port 8002

能力：
- GET  /health
- POST /rerank  { query, documents, top_n?, model?, stub? }
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 与主后端共用 backend/.env
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"), override=True)

logger = logging.getLogger("rerank_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RAG Rerank Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clean_secret(value: str | None) -> str:
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text


API_KEY = _clean_secret(
    os.getenv("OPENAI_API_KEY")
    or os.getenv("DASHSCOPE_API_KEY")
    or os.getenv("LLM_API_KEY")
    or ""
)
RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3-rerank")
RERANK_TIMEOUT = float(os.getenv("RERANK_TIMEOUT", "5.0") or 5.0)
# stub=true 时不调云，原序返回（联调探活用）
DEFAULT_STUB = os.getenv("RERANK_STUB", "false").lower() in ("1", "true", "yes", "on")


def _dashscope_rerank_url() -> str:
    return "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"


class RerankRequest(BaseModel):
    query: str
    documents: list[str] = Field(default_factory=list)
    top_n: int = Field(default=3, ge=1, le=50)
    model: str | None = None
    stub: bool | None = None


@app.get("/health")
async def health():
    mode = "stub" if DEFAULT_STUB or not API_KEY else "live"
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "status": "ok",
            "service": "rerank",
            "port": 8002,
            "mode": mode,
            "model": RERANK_MODEL,
            "has_api_key": bool(API_KEY),
        },
    }


@app.post("/rerank")
async def rerank(req: RerankRequest):
    docs = [str(d or "") for d in (req.documents or [])]
    top_n = min(max(int(req.top_n or 3), 1), max(len(docs), 1))
    model = (req.model or RERANK_MODEL).strip() or RERANK_MODEL
    use_stub = DEFAULT_STUB if req.stub is None else bool(req.stub)

    meta: dict[str, Any] = {
        "applied": False,
        "model": model,
        "fallback": None,
        "service": "rerank-8002",
        "stub": False,
    }

    if not docs:
        return {"code": 0, "msg": "success", "data": {"results": [], "meta": meta}}

    q = (req.query or "").strip()
    if not q:
        meta["fallback"] = "empty_query"
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "results": [
                    {"index": i, "relevance_score": 0.0} for i in range(min(top_n, len(docs)))
                ],
                "meta": meta,
            },
        }

    # stub：保持原序，联调拓扑可用
    if use_stub or not API_KEY:
        meta["stub"] = True
        meta["applied"] = True
        meta["fallback"] = None if use_stub else "no_api_key"
        results = [
            {"index": i, "relevance_score": round(1.0 - i * 0.01, 4)}
            for i in range(min(top_n, len(docs)))
        ]
        return {"code": 0, "msg": "success", "data": {"results": results, "meta": meta}}

    payload = {
        "model": model,
        "input": {"query": q, "documents": docs},
        "parameters": {"top_n": top_n},
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=RERANK_TIMEOUT, trust_env=False) as client:
            resp = await client.post(_dashscope_rerank_url(), json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("DashScope Rerank 失败，回退原序 stub: %s", e)
        meta["fallback"] = "api_error"
        meta["stub"] = True
        meta["applied"] = True
        results = [
            {"index": i, "relevance_score": round(1.0 - i * 0.01, 4)}
            for i in range(min(top_n, len(docs)))
        ]
        return {"code": 0, "msg": "success", "data": {"results": results, "meta": meta}}

    raw_results = ((body.get("output") or {}).get("results") or [])
    if not raw_results:
        meta["fallback"] = "empty_result"
        meta["stub"] = True
        meta["applied"] = True
        results = [{"index": i, "relevance_score": 0.0} for i in range(min(top_n, len(docs)))]
        return {"code": 0, "msg": "success", "data": {"results": results, "meta": meta}}

    out = []
    for item in raw_results:
        idx = int(item.get("index", -1))
        if idx < 0 or idx >= len(docs):
            continue
        score = item.get("relevance_score")
        out.append(
            {
                "index": idx,
                "relevance_score": float(score) if score is not None else 0.0,
            }
        )
    meta["applied"] = True
    return {"code": 0, "msg": "success", "data": {"results": out[:top_n], "meta": meta}}
