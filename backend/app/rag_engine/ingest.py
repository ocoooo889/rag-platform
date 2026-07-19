"""
文档入库：切片 → 向量化 → 写 SQLite chunks + Chroma
Embedding / Chroma 不可用时降级：仍写 SQLite 切片，status=degraded（仅 BM25）。
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.rag_engine.embedder import VectorStoreError, delete_from_chroma, embed_and_store
from app.rag_engine.splitter import split_file
from app.utils.ids import new_id
from app.utils.llm_client import EmbeddingServiceError

logger = logging.getLogger(__name__)

VECTOR_DEGRADED_MSG = "向量模型暂不可用，已切换关键词检索"
CHROMA_DEGRADED_MSG = "向量库（Chroma）未启动，已切换关键词检索"

# 进度回写节流：按 doc_id 记录上次写入时间
_progress_last_ts: dict[str, float] = {}
_PROGRESS_INTERVAL_SEC = 2.0


def _db_path() -> str:
    root = Path(__file__).resolve().parents[3]
    return str(root / config.LOCAL_DB_NAME)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _friendly_error(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    low = text.lower()
    if isinstance(exc, VectorStoreError) or "chroma" in low or "could not connect" in low:
        return getattr(exc, "message", None) or CHROMA_DEGRADED_MSG
    if "invalid_api_key" in low or "incorrect api key" in low or "401" in low:
        return "向量化失败：API Key 无效，请检查 .env 中的 OPENAI_API_KEY / DASHSCOPE_API_KEY"
    if isinstance(exc, EmbeddingServiceError) or VECTOR_DEGRADED_MSG in text:
        return VECTOR_DEGRADED_MSG
    if "embedding" in low or "embed" in low:
        return f"向量化失败：{text[:200]}"
    return f"文档处理失败：{text[:200]}"


async def ingest_document(
    kb_id: str,
    doc_id: str,
    file_path: str,
    filename: str | None = None,
) -> int:
    """
    对已存在于 documents 表中的文档做切片入库。
    向量失败 → status=degraded（关键词可用）；切片失败 → failed。
    """
    path = Path(file_path)
    if not path.exists():
        _mark_failed(doc_id, f"文件不存在: {file_path}")
        return 0

    filename = filename or path.name
    # 长文档切片可能较慢：尽早标 processing，避免 UI 一直 pending
    _set_status(doc_id, "processing", chunk_count=0, error_message=None)

    try:
        texts = split_file(str(path))
    except Exception as e:
        _mark_failed(doc_id, _friendly_error(e))
        logger.exception("切片失败 doc_id=%s", doc_id)
        return 0

    if not texts:
        _mark_failed(doc_id, "切片结果为空，请检查文档内容")
        return 0

    logger.info(
        "开始入库 doc_id=%s chunks=%s chunk_size=%s",
        doc_id,
        len(texts),
        config.CHUNK_SIZE,
    )

    conn = sqlite3.connect(_db_path())
    cur = conn.cursor()
    try:
        from app.db.schema_compat import ensure_rag_schema

        ensure_rag_schema(conn)
        cur.execute(
            "UPDATE documents SET status=?, chunk_count=?, error_message=?, updated_at=? WHERE id=?",
            ("processing", len(texts), f"向量化中 0/{len(texts)}", _now(), doc_id),
        )
        conn.commit()

        old = cur.execute(
            "SELECT chroma_id FROM chunks WHERE doc_id=?", (doc_id,)
        ).fetchall()
        if old:
            try:
                await delete_from_chroma([r[0] for r in old])
            except Exception as e:
                logger.warning("清理旧向量忽略: %s", e)
            cur.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
            conn.commit()

        chroma_ids = []
        metadatas = []
        rows = []
        for i, content in enumerate(texts):
            cid = new_id("c")
            chroma_ids.append(cid)
            metadatas.append({
                "doc_id": str(doc_id),
                "kb_id": str(kb_id),
                "source_doc": filename,
            })
            rows.append((cid, doc_id, kb_id, i, content, cid, _now()))

        def _on_progress(current: int, total: int) -> None:
            now_ts = time.monotonic()
            last = _progress_last_ts.get(doc_id, 0.0)
            # 首条 / 末条 / 间隔到时才写库
            if current not in (0, total) and (now_ts - last) < _PROGRESS_INTERVAL_SEC:
                return
            _progress_last_ts[doc_id] = now_ts
            try:
                cur.execute(
                    "UPDATE documents SET error_message=?, updated_at=? WHERE id=?",
                    (f"向量化中 {current}/{total}", _now(), doc_id),
                )
                conn.commit()
            except Exception as e:
                logger.debug("进度回写忽略 doc_id=%s: %s", doc_id, e)

        warn_msg = None
        try:
            await embed_and_store(
                texts, chroma_ids, metadatas=metadatas, progress_callback=_on_progress
            )
        except EmbeddingServiceError as e:
            warn_msg = VECTOR_DEGRADED_MSG
            logger.warning("Embedding 不可用，降级仅写切片 doc_id=%s: %s", doc_id, e)
        except VectorStoreError as e:
            warn_msg = e.message or CHROMA_DEGRADED_MSG
            logger.warning("Chroma 不可用，降级仅写切片 doc_id=%s: %s", doc_id, e)
        except Exception as e:
            warn_msg = _friendly_error(e)
            logger.warning("向量写入失败，降级仅写切片 doc_id=%s: %s", doc_id, e)

        cur.executemany(
            """
            INSERT INTO chunks (id, doc_id, kb_id, chunk_index, content, chroma_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        final_status = "degraded" if warn_msg else "completed"
        cur.execute(
            "UPDATE documents SET status=?, chunk_count=?, error_message=?, updated_at=? WHERE id=?",
            (final_status, len(texts), warn_msg, _now(), doc_id),
        )
        conn.commit()
        _progress_last_ts.pop(doc_id, None)
        try:
            from app.rag_engine.kb_index_cache import invalidate_kb_index

            invalidate_kb_index(kb_id)
        except Exception:
            pass
        return len(texts)
    except Exception as e:
        msg = _friendly_error(e)
        try:
            cur.execute(
                "UPDATE documents SET status=?, error_message=?, updated_at=? WHERE id=?",
                ("failed", msg, _now(), doc_id),
            )
            conn.commit()
        except Exception:
            logger.exception("写入失败状态异常 doc_id=%s", doc_id)
        logger.exception("入库失败 doc_id=%s: %s", doc_id, msg)
        return 0
    finally:
        conn.close()


def _set_status(
    doc_id: str,
    status: str,
    *,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    conn = sqlite3.connect(_db_path())
    try:
        from app.db.schema_compat import ensure_rag_schema

        ensure_rag_schema(conn)
        now = _now()
        if chunk_count is None:
            conn.execute(
                "UPDATE documents SET status=?, error_message=?, updated_at=? WHERE id=?",
                (status, error_message, now, doc_id),
            )
        else:
            conn.execute(
                "UPDATE documents SET status=?, chunk_count=?, error_message=?, updated_at=? WHERE id=?",
                (status, chunk_count, error_message, now, doc_id),
            )
        conn.commit()
    finally:
        conn.close()


def _mark_failed(doc_id: str, message: str) -> None:
    _set_status(doc_id, "failed", error_message=message)


async def ingest_text_for_dev(
    kb_id: str,
    doc_id: str,
    text: str,
    filename: str = "dev.md",
) -> int:
    """开发自测：不经过上传，直接对文本切片入库（需 documents 行已存在）"""
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        tmp = f.name
    try:
        return await ingest_document(kb_id, doc_id, tmp, filename=filename)
    finally:
        Path(tmp).unlink(missing_ok=True)
