"""
文档入库：切片 → 向量化 → 写 SQLite chunks + Chroma
Embedding 不可用时降级：仍写 SQLite 切片，检索侧走关键词（BM25）。
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.rag_engine.embedder import VectorStoreError, delete_from_chroma, embed_and_store
from app.rag_engine.splitter import SplitOptions, split_file_async
from app.utils.ids import new_id
from app.utils.llm_client import EmbeddingServiceError

logger = logging.getLogger(__name__)

VECTOR_DEGRADED_MSG = "向量模型暂不可用，已切换关键词检索"
CHROMA_DEGRADED_MSG = "向量库（Chroma）未启动，已切换关键词检索"


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
    split_options: SplitOptions | None = None,
) -> int:
    """
    对已存在于 documents 表中的文档做切片入库。
    Embedding 失败时降级为仅 SQLite 切片（关键词检索可用），status=completed。
    切片本身失败时才标记 failed。
    """
    path = Path(file_path)
    if not path.exists():
        _mark_failed(doc_id, f"文件不存在: {file_path}")
        return 0

    filename = filename or path.name
    opts = split_options or SplitOptions()
    try:
        split_result = await split_file_async(str(path), options=opts)
        texts = split_result.texts
        embed_texts = split_result.vectors_source()
        split_meta = split_result.meta
    except Exception as e:
        _mark_failed(doc_id, _friendly_error(e))
        logger.exception("切片失败 doc_id=%s", doc_id)
        return 0

    if not texts:
        _mark_failed(doc_id, "切片结果为空，请检查文档内容")
        return 0

    if len(embed_texts) != len(texts):
        # 防御：父子未对齐时回退为同一批文本
        embed_texts = texts

    conn = sqlite3.connect(_db_path())
    cur = conn.cursor()
    try:
        from app.db.schema_compat import ensure_rag_schema

        ensure_rag_schema(conn)
        import json

        cur.execute(
            """
            UPDATE documents
            SET status=?, chunk_count=?, error_message=?,
                split_strategy=?, chunk_size=?, chunk_overlap=?, split_meta=?
            WHERE id=?
            """,
            (
                "processing",
                0,
                None,
                split_meta.get("strategy") or opts.normalized_strategy(),
                int(split_meta.get("chunk_size") or opts.resolved_size()),
                int(split_meta.get("chunk_overlap") or opts.resolved_overlap()),
                json.dumps(split_meta, ensure_ascii=False),
                doc_id,
            ),
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
                "split_strategy": str(split_meta.get("strategy") or ""),
            })
            rows.append((cid, doc_id, kb_id, i, content, cid, _now()))

        warn_msg = None
        try:
            await embed_and_store(embed_texts, chroma_ids, metadatas=metadatas)
        except EmbeddingServiceError as e:
            warn_msg = VECTOR_DEGRADED_MSG
            logger.warning("Embedding 不可用，降级仅写切片 doc_id=%s: %s", doc_id, e)
        except VectorStoreError as e:
            warn_msg = e.message or CHROMA_DEGRADED_MSG
            logger.warning("Chroma 不可用，降级仅写切片 doc_id=%s: %s", doc_id, e)
        except Exception as e:
            # 其它异常：友好文案，仍写本地切片保证文档可用
            warn_msg = _friendly_error(e)
            logger.warning("向量写入失败，降级仅写切片 doc_id=%s: %s", doc_id, e)

        cur.executemany(
            """
            INSERT INTO chunks (id, doc_id, kb_id, chunk_index, content, chroma_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        cur.execute(
            "UPDATE documents SET status=?, chunk_count=?, error_message=? WHERE id=?",
            ("completed", len(texts), warn_msg, doc_id),
        )
        conn.commit()
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
                "UPDATE documents SET status=?, error_message=? WHERE id=?",
                ("failed", msg, doc_id),
            )
            conn.commit()
        except Exception:
            logger.exception("写入失败状态异常 doc_id=%s", doc_id)
        logger.exception("入库失败 doc_id=%s: %s", doc_id, msg)
        return 0
    finally:
        conn.close()


def _mark_failed(doc_id: str, message: str) -> None:
    conn = sqlite3.connect(_db_path())
    try:
        from app.db.schema_compat import ensure_rag_schema

        ensure_rag_schema(conn)
        conn.execute(
            "UPDATE documents SET status=?, error_message=? WHERE id=?",
            ("failed", message, doc_id),
        )
        conn.commit()
    finally:
        conn.close()


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
