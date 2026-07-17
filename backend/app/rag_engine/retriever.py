"""三种检索：vector / keyword / hybrid（契约 search_type）"""

from __future__ import annotations

from rank_bm25 import BM25Okapi

from app import config
from app.rag_engine.embedder import query_similar
from app.utils.llm_client import EmbeddingServiceError


def _tokenize(text: str) -> list[str]:
    return [c for c in text if not c.isspace()]


def _bm25_search(
    query: str,
    texts: list[str],
    ids: list[str],
    source_docs: list[str],
    doc_ids: list[str],
) -> list[dict]:
    if not texts:
        return []

    bm25 = BM25Okapi([_tokenize(t) for t in texts])
    scores = bm25.get_scores(_tokenize(query))
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
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


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
) -> list[dict]:
    top_n = min(max(top_n or config.DEFAULT_TOP_N, 1), config.MAX_TOP_N)
    search_type = (search_type or "hybrid").strip().lower()
    source_docs = source_docs or [""] * len(texts)
    doc_ids = doc_ids or ([doc_id or ""] * len(texts))

    if search_type == "keyword":
        return _bm25_search(query, texts, ids, source_docs, doc_ids)[:top_n]

    where = None
    if doc_id:
        where = {"doc_id": str(doc_id)}
    elif kb_id:
        where = {"kb_id": str(kb_id)}

    if search_type == "vector":
        try:
            hits = await query_similar(query, top_n, where=where)
            # 用本地库回填，保证 content/source_doc 完整
            local = {cid: i for i, cid in enumerate(ids)}
            for h in hits:
                if h["chunk_id"] in local:
                    i = local[h["chunk_id"]]
                    h["content"] = texts[i]
                    h["source_doc"] = source_docs[i] or h.get("source_doc", "")
                    h["doc_id"] = doc_ids[i] or h.get("doc_id", "")
            return hits[:top_n]
        except EmbeddingServiceError:
            return _bm25_search(query, texts, ids, source_docs, doc_ids)[:top_n]

    # hybrid
    try:
        vector_hits = await query_similar(query, top_n * 2, where=where)
    except EmbeddingServiceError:
        return _bm25_search(query, texts, ids, source_docs, doc_ids)[:top_n]

    keyword_hits = _bm25_search(query, texts, ids, source_docs, doc_ids)

    combined: dict[str, dict] = {}
    for i, cid in enumerate(ids):
        combined[cid] = {
            "chunk_id": cid,
            "content": texts[i],
            "score": 0.0,
            "source_doc": source_docs[i],
            "doc_id": doc_ids[i],
            "_v": 0.0,
            "_k": 0.0,
        }

    for h in vector_hits:
        cid = h["chunk_id"]
        if cid not in combined:
            combined[cid] = {
                "chunk_id": cid,
                "content": h.get("content", ""),
                "score": 0.0,
                "source_doc": h.get("source_doc", ""),
                "doc_id": h.get("doc_id", "") or (doc_id or ""),
                "_v": 0.0,
                "_k": 0.0,
            }
        combined[cid]["_v"] = float(h.get("score") or 0.0)
        if h.get("content"):
            combined[cid]["content"] = h["content"]

    for h in keyword_hits:
        cid = h["chunk_id"]
        if cid in combined:
            combined[cid]["_k"] = float(h.get("score") or 0.0)

    for item in combined.values():
        item["score"] = round(
            config.HYBRID_ALPHA * item["_v"] + config.BM25_WEIGHT * item["_k"],
            4,
        )
        item.pop("_v", None)
        item.pop("_k", None)

    results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    results = [r for r in results if r["score"] > 0] or results
    return results[:top_n]
