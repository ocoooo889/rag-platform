"""轻量 SQLite 访问（3号检索/对话用，不抢 4号 ORM 设计）"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app import config

_schema_checked = False


def get_conn() -> sqlite3.Connection:
    global _schema_checked
    root = Path(__file__).resolve().parents[3]
    db_path = root / config.LOCAL_DB_NAME
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if not _schema_checked:
        from app.db.schema_compat import ensure_rag_schema

        ensure_rag_schema(conn)
        _schema_checked = True
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


def get_session_kb_id(session_id: str) -> str | None:
    """取会话所属 kb_id；会话不存在返回 None"""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT kb_id FROM conversations
            WHERE session_id=? AND kb_id IS NOT NULL
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        return row["kb_id"] if row else None


def list_chat_sessions(
    kb_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    按知识库分页列出会话。
    title = 首条 user 消息；last_message = 最新一条消息内容。
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    with get_conn() as conn:
        total = conn.execute(
            """
            SELECT COUNT(DISTINCT session_id) AS c
            FROM conversations
            WHERE kb_id=?
            """,
            (kb_id,),
        ).fetchone()["c"]

        rows = conn.execute(
            """
            WITH session_meta AS (
                SELECT session_id, MAX(created_at) AS updated_at
                FROM conversations
                WHERE kb_id=?
                GROUP BY session_id
            )
            SELECT
                sm.session_id AS session_id,
                sm.updated_at AS updated_at,
                (
                    SELECT c.content FROM conversations c
                    WHERE c.session_id = sm.session_id AND c.role = 'user'
                    ORDER BY c.created_at ASC, c.rowid ASC
                    LIMIT 1
                ) AS title,
                (
                    SELECT c.content FROM conversations c
                    WHERE c.session_id = sm.session_id
                    ORDER BY c.created_at DESC, c.rowid DESC
                    LIMIT 1
                ) AS last_message
            FROM session_meta sm
            ORDER BY sm.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (kb_id, page_size, offset),
        ).fetchall()

    items = [
        {
            "session_id": r["session_id"],
            "title": r["title"] or "",
            "last_message": r["last_message"] or "",
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
    return items, int(total)


def list_chat_messages(
    session_id: str,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[sqlite3.Row], int]:
    """按会话分页列出消息（按时间升序）"""
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(1) AS c FROM conversations WHERE session_id=?",
            (session_id,),
        ).fetchone()["c"]
        rows = conn.execute(
            """
            SELECT id, role, content, "references", created_at
            FROM conversations
            WHERE session_id=?
            ORDER BY created_at ASC, rowid ASC
            LIMIT ? OFFSET ?
            """,
            (session_id, page_size, offset),
        ).fetchall()
    return list(rows), int(total)


def delete_chat_session(session_id: str) -> int:
    """删除会话下全部消息，返回删除行数"""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE session_id=?",
            (session_id,),
        )
        conn.commit()
        return int(cur.rowcount)
