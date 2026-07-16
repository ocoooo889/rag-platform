"""Chroma 向量写入 / 查询 / 删除（按 kb_id、doc_id 隔离）"""

from __future__ import annotations

import logging

import chromadb

from app import config
from app.utils.llm_client import get_embedding, get_embeddings_batch

logger = logging.getLogger(__name__)


def _get_collection():
    client = chromadb.HttpClient(host=config.CHROMA_HOST, port=config.CHROMA_PORT)
    return client.get_or_create_collection(name=config.CHROMA_COLLECTION_NAME)


def _distance_to_score(distance) -> float:
    """Chroma 距离 → 0~1 相似度"""
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return 0.0
    return round(1.0 / (1.0 + max(d, 0.0)), 4)


async def embed_and_store(
    texts: list[str],
    ids: list[str],
    metadatas: list[dict] | None = None,
) -> None:
    embeddings = await get_embeddings_batch(texts)
    collection = _get_collection()
    kwargs = {"embeddings": embeddings, "documents": texts, "ids": ids}
    if metadatas:
        kwargs["metadatas"] = metadatas
    collection.add(**kwargs)
    logger.info("写入 Chroma %s 条，集合=%s", len(texts), config.CHROMA_COLLECTION_NAME)


async def query_similar(
    query: str,
    top_n: int = 3,
    where: dict | None = None,
) -> list[dict]:
    query_vec = await get_embedding(query)
    collection = _get_collection()
    n_results = max(top_n, 1)
    # Chroma 要求 n_results 不超过集合大小时更稳，这里先按请求取
    kwargs = {
        "query_embeddings": [query_vec],
        "n_results": n_results,
        "include": ["documents", "distances", "metadatas"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    hits = []
    if not results.get("ids") or not results["ids"][0]:
        return hits

    for i, cid in enumerate(results["ids"][0]):
        meta = {}
        if results.get("metadatas") and results["metadatas"][0]:
            meta = results["metadatas"][0][i] or {}
        dist = None
        if results.get("distances") and results["distances"][0]:
            dist = results["distances"][0][i]
        hits.append({
            "chunk_id": cid,
            "content": results["documents"][0][i] if results.get("documents") else "",
            "score": _distance_to_score(dist),
            "source_doc": meta.get("source_doc", "") or "",
            "doc_id": meta.get("doc_id", "") or "",
        })
    return hits


async def delete_from_chroma(ids: list[str]) -> None:
    if not ids:
        return
    collection = _get_collection()
    collection.delete(ids=ids)
