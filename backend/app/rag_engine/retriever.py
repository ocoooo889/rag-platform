"""三种检索：vector / keyword / hybrid（契约 search_type）"""

from __future__ import annotations

import asyncio
import logging

from rank_bm25 import BM25Okapi

from app import config
from app.rag_engine.embedder import VectorStoreError, query_similar
from app.utils.llm_client import EmbeddingServiceError

logger = logging.getLogger(__name__)

# jieba 可选：未安装时回退按字切分，保证检索仍可用
_jieba = None
try:
    import jieba  # type: ignore

    _jieba = jieba
except Exception as e:  # noqa: BLE001 — 缺依赖时降级即可
    logger.warning("jieba 未可用，BM25 回退按字切分: %s", e)


def _tokenize(text: str) -> list[str]:
    """中文优先 jieba 分词；失败或空结果时回退按字切分"""
    raw = text or ""
    if _jieba is not None:
        try:
            tokens = [t.strip() for t in _jieba.lcut(raw) if t and not t.isspace()]
            if tokens:
                return tokens
        except Exception as e:  # noqa: BLE001
            logger.warning("jieba 分词失败，回退按字: %s", e)
    return [c for c in raw if not c.isspace()]


def _bm25_search(
    query: str,
    texts: list[str],
    ids: list[str],
    source_docs: list[str],
    doc_ids: list[str],
    *,
    bm25: BM25Okapi | None = None,
) -> list[dict]:
    if not texts:
        return []

    engine = bm25 or BM25Okapi([_tokenize(t) for t in texts])
    scores = engine.get_scores(_tokenize(query))
    min_s = float(min(scores))
    max_s = float(max(scores))
    span = max_s - min_s

    results = []
    for i, raw in enumerate(scores):
        norm = ((float(raw) - min_s) / span) if span > 0 else (0.0 if max_s == 0 else 1.0)
        results.append({
            "chunk_id": ids[i],
            "content": texts[i],
            "score": round(norm, 4),
            "source_doc": source_docs[i] if i < len(source_docs) else "",
            "doc_id": doc_ids[i] if i < len(doc_ids) else "",
            "method": "bm25",
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _mark_bm25_fallback(hits: list[dict]) -> list[dict]:
    for h in hits:
        h["retrieve_fallback"] = "bm25"
        h["method"] = "bm25"
    return hits


def _resolve_enable_rerank(enable_rerank: bool | None) -> bool:
    """请求级覆盖；None 时跟随全局 ENABLE_RERANK。"""
    if enable_rerank is None:
        return bool(getattr(config, "ENABLE_RERANK", False))
    return bool(enable_rerank)


def _new_retrieve_meta(search_type: str, *, enable_rerank: bool = False) -> dict:
    """构建检索过程 meta，供 pipeline / 接口回显。"""
    mode = str(getattr(config, "CHAT_RETRIEVE_MODE", "balanced") or "balanced").lower()
    return {
        "search_type": search_type,
        "retrieve_mode": mode,
        "effective_search_type": search_type,
        "fallback": None,
        "rerank": {
            "enabled": enable_rerank,
            "applied": False,
            "model": getattr(config, "RERANK_MODEL", "qwen3-rerank"),
            "service": "rerank-8002",
        },
    }


async def _maybe_rerank(
    query: str,
    hits: list[dict],
    *,
    top_n: int,
    meta: dict,
    enable_rerank: bool | None = None,
) -> list[dict]:
    from app.rag_engine.reranker import rerank_hits

    if not hits:
        return hits[:top_n]
    reranked, rerank_meta = await rerank_hits(
        query, hits, top_n=top_n, enabled=enable_rerank
    )
    meta["rerank"] = rerank_meta
    if rerank_meta.get("applied"):
        meta["effective_search_type"] = f"{meta.get('effective_search_type', '')}+rerank"
    return reranked


async def retrieve(
    query: str,
    texts: list[str],
    ids: list[str],
    search_type: str = "hybrid",
    top_n: int = 3,
    *,
    doc_id: str | None = None,
    kb_id: str | None = None,
    source_docs: list[str] | None = None,
    doc_ids: list[str] | None = None,
    enable_rerank: bool | None = None,
    purpose: str = "chat",
) -> tuple[list[dict], dict]:
    """
    purpose:
      - chat: 应用 CHAT_RETRIEVE_MODE + CHAT_VECTOR_TIMEOUT
      - hittest: 不做 fast 短路，使用 HITTEST_VECTOR_TIMEOUT
    """
    top_n = min(max(top_n or config.DEFAULT_TOP_N, 1), config.MAX_TOP_N)
    search_type = (search_type or "hybrid").strip().lower()
    purpose = (purpose or "chat").strip().lower()
    rerank_on = _resolve_enable_rerank(enable_rerank)
    meta = _new_retrieve_meta(search_type, enable_rerank=rerank_on)
    source_docs = source_docs or [""] * len(texts)
    doc_ids = doc_ids or ([doc_id or ""] * len(texts))

    cached_bm25 = None
    if kb_id and not doc_id:
        try:
            from app.rag_engine.kb_index_cache import get_kb_index

            idx = get_kb_index(str(kb_id))
            # 调用方传入的 texts 与缓存一致时复用 BM25，跳过全库分词
            if idx.texts is texts or (
                len(idx.texts) == len(texts) and idx.ids == ids
            ):
                cached_bm25 = idx.bm25
                texts = idx.texts
                ids = idx.ids
                source_docs = idx.source_docs
                doc_ids = idx.doc_ids
        except Exception as e:  # noqa: BLE001
            logger.debug("BM25 缓存未命中: %s", e)

    if search_type == "keyword":
        hits = _bm25_search(
            query, texts, ids, source_docs, doc_ids, bm25=cached_bm25
        )[:top_n]
        meta["effective_search_type"] = "keyword"
        return await _maybe_rerank(
            query, hits, top_n=top_n, meta=meta, enable_rerank=rerank_on
        ), meta

    where = None
    if doc_id:
        where = {"doc_id": str(doc_id)}
    elif kb_id:
        where = {"kb_id": str(kb_id)}

    if search_type == "vector":
        mode = str(getattr(config, "CHAT_RETRIEVE_MODE", "balanced") or "balanced").lower()
        if purpose == "hittest":
            timeout = float(getattr(config, "HITTEST_VECTOR_TIMEOUT", 10) or 10)
            # 命中测试始终真走向量，不受 chat fast 短路影响
            apply_fast = False
            wait_quality = False
        else:
            timeout = float(getattr(config, "CHAT_VECTOR_TIMEOUT", 0) or 0)
            apply_fast = mode == "fast"
            wait_quality = mode == "quality"

        if apply_fast:
            # 主动走关键词优先，不算「向量失败降级」
            hits = _bm25_search(
                query, texts, ids, source_docs, doc_ids, bm25=cached_bm25
            )[:top_n]
            meta["effective_search_type"] = "keyword"
            meta["retrieve_mode"] = "fast"
            return await _maybe_rerank(
                query, hits, top_n=top_n, meta=meta, enable_rerank=rerank_on
            ), meta

        async def _vector():
            hits = await query_similar(query, top_n, where=where)
            local = {cid: i for i, cid in enumerate(ids)}
            for h in hits:
                if h["chunk_id"] in local:
                    i = local[h["chunk_id"]]
                    h["content"] = texts[i]
                    h["source_doc"] = source_docs[i] or h.get("source_doc", "")
                    h["doc_id"] = doc_ids[i] or h.get("doc_id", "")
                h["method"] = "vector"
            return hits[:top_n]

        try:
            if timeout > 0 and not wait_quality:
                hits = await asyncio.wait_for(_vector(), timeout=timeout)
            else:
                hits = await _vector()
            meta["effective_search_type"] = "vector"
            return await _maybe_rerank(
                query, hits, top_n=top_n, meta=meta, enable_rerank=rerank_on
            ), meta
        except asyncio.TimeoutError:
            logger.info("向量检索超时 %.2fs（purpose=%s），回退 BM25", timeout, purpose)
            meta["fallback"] = "bm25"
            meta["effective_search_type"] = "vector->bm25"
            hits = _mark_bm25_fallback(
                _bm25_search(
                    query, texts, ids, source_docs, doc_ids, bm25=cached_bm25
                )[:top_n]
            )
            return await _maybe_rerank(
                query, hits, top_n=top_n, meta=meta, enable_rerank=rerank_on
            ), meta
        except (EmbeddingServiceError, VectorStoreError):
            meta["fallback"] = "bm25"
            meta["effective_search_type"] = "vector->bm25"
            hits = _mark_bm25_fallback(
                _bm25_search(
                    query, texts, ids, source_docs, doc_ids, bm25=cached_bm25
                )[:top_n]
            )
            return await _maybe_rerank(
                query, hits, top_n=top_n, meta=meta, enable_rerank=rerank_on
            ), meta

    # hybrid：向量 / BM25 各取候选集并集再融合，避免对全库 chunk 初始化打分表
    cand_mul = max(
        config.HYBRID_CANDIDATE_MUL,
        int(getattr(config, "RERANK_CANDIDATE_MUL", 5) or 5) if rerank_on else 1,
    )
    try:
        cand_n = max(top_n * cand_mul, top_n)
        vector_hits = await query_similar(query, cand_n, where=where)
    except (EmbeddingServiceError, VectorStoreError):
        meta["fallback"] = "bm25"
        meta["effective_search_type"] = "hybrid->bm25"
        hits = _mark_bm25_fallback(
            _bm25_search(
                query, texts, ids, source_docs, doc_ids, bm25=cached_bm25
            )[:top_n]
        )
        return await _maybe_rerank(
            query, hits, top_n=top_n, meta=meta, enable_rerank=rerank_on
        ), meta

    keyword_hits = _bm25_search(
        query, texts, ids, source_docs, doc_ids, bm25=cached_bm25
    )[:cand_n]
    local = {cid: i for i, cid in enumerate(ids)}

    combined: dict[str, dict] = {}

    def _ensure(cid: str, *, content: str = "", source_doc: str = "", doc_id_val: str = "") -> dict:
        if cid not in combined:
            i = local.get(cid)
            combined[cid] = {
                "chunk_id": cid,
                "content": texts[i] if i is not None else content,
                "score": 0.0,
                "source_doc": (source_docs[i] if i is not None else "") or source_doc,
                "doc_id": (doc_ids[i] if i is not None else "") or doc_id_val or (doc_id or ""),
                "_v": 0.0,
                "_k": 0.0,
            }
        return combined[cid]

    for h in vector_hits:
        cid = h["chunk_id"]
        item = _ensure(
            cid,
            content=h.get("content", ""),
            source_doc=h.get("source_doc", ""),
            doc_id_val=h.get("doc_id", "") or (doc_id or ""),
        )
        item["_v"] = float(h.get("score") or 0.0)
        if h.get("content"):
            item["content"] = h["content"]

    for h in keyword_hits:
        cid = h["chunk_id"]
        item = _ensure(
            cid,
            content=h.get("content", ""),
            source_doc=h.get("source_doc", ""),
            doc_id_val=h.get("doc_id", "") or (doc_id or ""),
        )
        item["_k"] = float(h.get("score") or 0.0)

    for item in combined.values():
        v, k = float(item["_v"]), float(item["_k"])
        item["score"] = round(
            config.HYBRID_ALPHA * v + config.BM25_WEIGHT * k,
            4,
        )
        if v > 0 and k > 0:
            item["method"] = "hybrid"
        elif v > 0:
            item["method"] = "vector"
        else:
            item["method"] = "bm25"
        item.pop("_v", None)
        item.pop("_k", None)

    results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    results = [r for r in results if r["score"] > 0] or results
    meta["effective_search_type"] = "hybrid"
    hits = results[:cand_n]
    hits = await _maybe_rerank(
        query, hits, top_n=top_n, meta=meta, enable_rerank=rerank_on
    )
    return hits, meta
