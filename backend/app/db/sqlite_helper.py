"""轻量 SQLite 访问（3号检索/对话用，不抢 4号 ORM 设计）"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app import config


def get_conn() -> sqlite3.Connection:
    root = Path(__file__).resolve().parents[3]
    db_path = root / config.LOCAL_DB_NAME
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def kb_exists(kb_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM knowledge_bases WHERE id=?", (kb_id,)
        ).fetchone()
        return row is not None


def get_document(doc_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE id=?", (doc_id,)
        ).fetchone()


def count_docs_by_kb(kb_id: str) -> tuple[int, int]:
    """返回 (文档总数, 非 completed 数量)，供对话侧 4002 准入判断"""
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(1) AS c FROM documents WHERE kb_id=?", (kb_id,)
        ).fetchone()["c"]
        pending = conn.execute(
            """
            SELECT COUNT(1) AS c FROM documents
            WHERE kb_id=? AND status != 'completed'
            """,
            (kb_id,),
        ).fetchone()["c"]
        return int(total), int(pending)


def load_chunks_by_doc(doc_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, content, chroma_id, doc_id, kb_id
            FROM chunks WHERE doc_id=? ORDER BY chunk_index
            """,
            (doc_id,),
        ).fetchall()


def load_chunks_by_kb(kb_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT c.id, c.content, c.chroma_id, c.doc_id, c.kb_id, d.filename
            FROM chunks c
            JOIN documents d ON c.doc_id = d.id
            WHERE c.kb_id=? AND d.status='completed'
            ORDER BY c.doc_id, c.chunk_index
            """,
            (kb_id,),
        ).fetchall()


def load_chat_history(session_id: str, max_rounds: int = 10) -> list[sqlite3.Row]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM conversations
            WHERE session_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, max_rounds * 2),
        ).fetchall()
    return list(reversed(rows))


def save_conversation(
    msg_id: str,
    session_id: str,
    kb_id: str,
    role: str,
    content: str,
    references_json: str | None,
    created_at: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, session_id, kb_id, role, content, "references", created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, session_id, kb_id, role, content, references_json, created_at),
        )
        conn.commit()
