"""联调 schema 兼容（3号：B ORM 建表缺字段/缺表时补齐，不修改 4号 models 定义）"""

from __future__ import annotations

import sqlite3


def ensure_rag_schema(conn: sqlite3.Connection) -> None:
    """确保 ingest / chat 依赖的 chunks 字段与 conversations 表存在。"""
    doc_rows = conn.execute("PRAGMA table_info(documents)").fetchall()
    if doc_rows:
        doc_names = {r[1] for r in doc_rows}
        if "error_message" not in doc_names:
            conn.execute("ALTER TABLE documents ADD COLUMN error_message TEXT")
            conn.commit()

    rows = conn.execute("PRAGMA table_info(chunks)").fetchall()
    if rows:
        names = {r[1] for r in rows}
        if "chunk_index" not in names:
            conn.execute(
                "ALTER TABLE chunks ADD COLUMN chunk_index INTEGER NOT NULL DEFAULT 0"
            )
        if "created_at" not in names:
            conn.execute("ALTER TABLE chunks ADD COLUMN created_at TEXT")
        conn.commit()

    has_conv = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversations'"
    ).fetchone()
    if not has_conv:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL,
                kb_id       TEXT,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                "references" TEXT,
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conv_session_id ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_conv_session_created
                ON conversations(session_id, created_at);
            """
        )
        conn.commit()
