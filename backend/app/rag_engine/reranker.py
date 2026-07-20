"""
检索结果 Rerank（可选）。

优先调用 DashScope Text ReRank；失败时保持原排序（不阻断主链路）。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app import config

logger = logging.getLogger(__name__)


def _dashscope_rerank_url() -> str:
    base = (config.OPENAI_BASE_URL or "").rstrip("/")
    if "compatible-mode" in base:
        return "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
    if "dashscope" in base:
        return f"{base.split('/compatible-mode')[0]}/api/v1/services/rerank/text-rerank/text-rerank"
    return "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"


async def rerank_hits(
    query: str,
    hits: list[dict[str, Any]],
    *,
    top_n: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    对候选片段重排序。
    返回 (rerank 后 hits, meta)。
    """
    meta: dict[str, Any] = {
        "enabled": bool(getattr(config, "ENABLE_RERANK", False)),
        "applied": False,
        "model": getattr(config, "RERANK_MODEL", "gte-rerank"),
        "fallback": None,
    }
    if not meta["enabled"] or not hits:
        return hits[:top_n], meta

    q = (query or "").strip()
    if not q:
        return hits[:top_n], meta

    documents = [str(h.get("content") or "") for h in hits]
    if not any(documents):
        return hits[:top_n], meta

    api_key = (config.OPENAI_API_KEY or "").strip()
    if not api_key:
        meta["fallback"] = "no_api_key"
        logger.info("Rerank 跳过：未配置 API Key")
        return hits[:top_n], meta

    payload = {
        "model": meta["model"],
        "input": {"query": q, "documents": documents},
        "parameters": {"top_n": min(max(top_n, 1), len(documents))},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    timeout = float(getattr(config, "RERANK_TIMEOUT", 3.0) or 3.0)

    try:
        # trust_env=False：绕过本机失效系统代理（与 embedder 一致）
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            resp = await client.post(_dashscope_rerank_url(), json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
    except Exception as e:  # noqa: BLE001
        meta["fallback"] = "api_error"
        logger.warning("Rerank API 失败，保持原排序: %s", e)
        return hits[:top_n], meta

    results = ((body.get("output") or {}).get("results") or [])
    if not results:
        meta["fallback"] = "empty_result"
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
