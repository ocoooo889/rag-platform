"""知识库分片 / BM25 内存缓存，避免每次对话全表加载与全库分词。"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.db.sqlite_helper import load_chunks_by_kb

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_cache: dict[str, "KbIndexCache"] = {}

_jieba = None
try:
    import jieba  # type: ignore

    _jieba = jieba
except Exception:  # noqa: BLE001
    _jieba = None


def _tokenize(text: str) -> list[str]:
    raw = text or ""
    if _jieba is not None:
        try:
            tokens = [t.strip() for t in _jieba.lcut(raw) if t and not t.isspace()]
            if tokens:
                return tokens
        except Exception:  # noqa: BLE001
            pass
    return [c for c in raw if not c.isspace()]


@dataclass
class KbIndexCache:
    texts: list[str]
    ids: list[str]
    source_docs: list[str]
    doc_ids: list[str]
    tokenized: list[list[str]]
    bm25: BM25Okapi | None
    fingerprint: str


def _fingerprint(rows) -> str:
    if not rows:
        return "0"
    first = rows[0]["chroma_id"] or rows[0]["id"]
    last = rows[-1]["chroma_id"] or rows[-1]["id"]
    return f"{len(rows)}:{first}:{last}"


def invalidate_kb_index(kb_id: str | None = None) -> None:
    with _lock:
        if kb_id is None:
            _cache.clear()
            return
        _cache.pop(str(kb_id), None)


def get_kb_index(kb_id: str) -> KbIndexCache:
    key = str(kb_id)
    with _lock:
        hit = _cache.get(key)
        if hit is not None:
            return hit

    rows = load_chunks_by_kb(key)
    texts = [r["content"] for r in rows]
    ids = [r["chroma_id"] or r["id"] for r in rows]
    source_docs = [r["filename"] if "filename" in r.keys() else "" for r in rows]
    doc_ids = [r["doc_id"] for r in rows]
    fp = _fingerprint(rows)

    tokenized: list[list[str]] = []
    bm25: BM25Okapi | None = None
    if texts:
        tokenized = [_tokenize(t) for t in texts]
        bm25 = BM25Okapi(tokenized)

    entry = KbIndexCache(
        texts=texts,
        ids=ids,
        source_docs=source_docs,
        doc_ids=doc_ids,
        tokenized=tokenized,
        bm25=bm25,
        fingerprint=fp,
    )
    with _lock:
        _cache[key] = entry
        logger.info("KB index cached kb_id=%s chunks=%s", key, len(texts))
    return entry


def prepare_chunk_rows(kb_id: str) -> tuple[list[str], list[str], list[str], list[str]]:
    idx = get_kb_index(kb_id)
    return idx.texts, idx.ids, idx.source_docs, idx.doc_ids
