"""
文档入库：切片 → 向量化 → 写 SQLite chunks + Chroma
供 4号上传后调用，也可自测脚本直接调用
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.rag_engine.embedder import delete_from_chroma, embed_and_store
from app.rag_engine.splitter import split_file, split_text
from app.utils.ids import new_id


def _db_path() -> str:
    root = Path(__file__).resolve().parents[3]
    return str(root / config.LOCAL_DB_NAME)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


async def ingest_document(
    kb_id: str,
    doc_id: str,
    file_path: str,
    filename: str | None = None,
) -> int:
    """
    对已存在于 documents 表中的文档做切片入库。
    返回切片数量。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    filename = filename or path.name
    texts = split_file(str(path))
    if not texts:
        raise ValueError("切片结果为空，请检查文档内容")

    conn = sqlite3.connect(_db_path())
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE documents SET status=?, chunk_count=? WHERE id=?",
            ("processing", 0, doc_id),
        )
        conn.commit()

        # 清掉旧分片（重新入库场景）
        old = cur.execute(
            "SELECT chroma_id FROM chunks WHERE doc_id=?", (doc_id,)
        ).fetchall()
        if old:
            await delete_from_chroma([r[0] for r in old])
            cur.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
            conn.commit()

        chunk_ids = []
        chroma_ids = []
        metadatas = []
        rows = []
        for i, content in enumerate(texts):
            cid = new_id("c")
            chunk_ids.append(cid)
            chroma_ids.append(cid)
            metadatas.append({
                "doc_id": str(doc_id),
                "kb_id": str(kb_id),
                "source_doc": filename,
            })
            rows.append((cid, doc_id, kb_id, i, content, cid, _now()))

        await embed_and_store(texts, chroma_ids, metadatas=metadatas)

        cur.executemany(
            """
            INSERT INTO chunks (id, doc_id, kb_id, chunk_index, content, chroma_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        cur.execute(
            "UPDATE documents SET status=?, chunk_count=? WHERE id=?",
            ("completed", len(texts), doc_id),
        )
        conn.commit()
        return len(texts)
    except Exception:
        cur.execute(
            "UPDATE documents SET status=? WHERE id=?",
            ("failed", doc_id),
        )
        conn.commit()
        raise
    finally:
        conn.close()


async def ingest_text_for_dev(
    kb_id: str,
    doc_id: str,
    text: str,
    filename: str = "dev.md",
) -> int:
    """开发自测：不经过上传，直接对文本切片入库（需 documents 行已存在）"""
    texts = split_text(text)
    # 写临时文件再走统一逻辑更简单：直接内联
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        tmp = f.name
    try:
        return await ingest_document(kb_id, doc_id, tmp, filename=filename)
    finally:
        Path(tmp).unlink(missing_ok=True)
