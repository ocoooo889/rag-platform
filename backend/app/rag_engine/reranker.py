"""
检索结果 Rerank：优先调用本机 8002 微服务；失败时保持原排序。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app import config

logger = logging.getLogger(__name__)


def _service_base() -> str:
    return str(
        getattr(config, "RERANK_SERVICE_URL", None) or "http://127.0.0.1:8002"
    ).rstrip("/")


async def probe_rerank_service() -> tuple[bool, str, dict]:
    """探测 8002 健康；返回 (ok, detail, data)。"""
    url = f"{_service_base()}/health"
    try:
        async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            body = resp.json()
            data = body.get("data") if isinstance(body, dict) else {}
            mode = (data or {}).get("mode") or "unknown"
            model = (data or {}).get("model") or ""
            detail = f"127.0.0.1:8002 · {mode}"
            if model:
                detail += f" · {model}"
            return True, detail, data or {}
    except Exception as e:  # noqa: BLE001
        return False, f"8002 不可达: {e}", {}


async def rerank_hits(
    query: str,
    hits: list[dict[str, Any]],
    *,
    top_n: int,
    enabled: bool | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    对候选片段重排序（经 8002）。
    enabled=None 时跟随 config.ENABLE_RERANK。
    """
    use = bool(getattr(config, "ENABLE_RERANK", False)) if enabled is None else bool(enabled)
    meta: dict[str, Any] = {
        "enabled": use,
        "applied": False,
        "model": getattr(config, "RERANK_MODEL", "qwen3-rerank"),
        "fallback": None,
        "service": "rerank-8002",
    }
    if not use or not hits:
        return hits[:top_n], meta

    q = (query or "").strip()
    if not q:
        return hits[:top_n], meta

    documents = [str(h.get("content") or "") for h in hits]
    if not any(documents):
        return hits[:top_n], meta

    payload = {
        "query": q,
        "documents": documents,
        "top_n": min(max(top_n, 1), len(documents)),
        "model": meta["model"],
    }
    timeout = float(getattr(config, "RERANK_TIMEOUT", 5.0) or 5.0)
    url = f"{_service_base()}/rerank"

    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
    except Exception as e:  # noqa: BLE001
        meta["fallback"] = "service_error"
        logger.warning("Rerank 服务调用失败，保持原排序: %s", e)
        return hits[:top_n], meta

    data = body.get("data") if isinstance(body, dict) else {}
    svc_meta = (data or {}).get("meta") or {}
    results = (data or {}).get("results") or []
    if svc_meta:
        meta["model"] = svc_meta.get("model") or meta["model"]
        if svc_meta.get("fallback"):
            meta["fallback"] = svc_meta.get("fallback")
        if svc_meta.get("stub"):
            meta["stub"] = True

    if not results:
        meta["fallback"] = meta.get("fallback") or "empty_result"
        return hits[:top_n], meta

    reranked: list[dict[str, Any]] = []
    for item in results:
        idx = int(item.get("index", -1))
        if idx < 0 or idx >= len(hits):
            continue
        hit = dict(hits[idx])
        score = item.get("relevance_score")
        if score is not None:
            hit["score"] = round(float(score), 4)
        hit["reranked"] = True
        reranked.append(hit)

    if not reranked:
        meta["fallback"] = "parse_error"
        return hits[:top_n], meta

    meta["applied"] = True
    return reranked[:top_n], meta
