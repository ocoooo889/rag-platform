"""
智能 RAG 平台 — 数据库一键初始化脚本
用途：读取 db_schema.md 中的建表 SQL 并执行
使用：python scripts/init_db.py
"""

import os
import sys
import sqlite3

# 加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# --- 读取环境变量 ---
ENV = os.getenv("ENV", "dev-default")
DB_NAME = os.getenv("LOCAL_DB_NAME", f"{ENV}_rag.db")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DB_NAME)

print(f"[init_db] 环境: {ENV}")
print(f"[init_db] 数据库路径: {DB_PATH}")

# --- 建表 SQL（与 docs/db_schema.md 保持一致） ---
SQL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS roles (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        description TEXT DEFAULT '',
        permissions TEXT DEFAULT '[]',
        created_at  TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);",
    """
    CREATE TABLE IF NOT EXISTS users (
        id            TEXT PRIMARY KEY,
        username      TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        display_name  TEXT NOT NULL,
        role_id       TEXT REFERENCES roles(id) ON DELETE RESTRICT,
        status        TEXT NOT NULL DEFAULT 'active',
        created_at    TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
    "CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);",
    """
    CREATE TABLE IF NOT EXISTS knowledge_bases (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        description TEXT DEFAULT '',
        created_by  TEXT REFERENCES users(id),
        created_at  TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_kb_name ON knowledge_bases(name);",
    "CREATE INDEX IF NOT EXISTS idx_kb_created_by ON knowledge_bases(created_by);",
    """
    CREATE TABLE IF NOT EXISTS documents (
        id          TEXT PRIMARY KEY,
        kb_id       TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
        filename    TEXT NOT NULL,
        file_type   TEXT NOT NULL,
        file_size   INTEGER NOT NULL,
        file_path   TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'pending',
        chunk_count INTEGER DEFAULT 0,
        uploaded_by TEXT REFERENCES users(id),
        uploaded_at TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_doc_kb_id ON documents(kb_id);",
    "CREATE INDEX IF NOT EXISTS idx_doc_status ON documents(status);",
    "CREATE INDEX IF NOT EXISTS idx_doc_kb_status ON documents(kb_id, status);",
    """
    CREATE TABLE IF NOT EXISTS chunks (
        id          TEXT PRIMARY KEY,
        doc_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        kb_id       TEXT NOT NULL REFERENCES knowledge_bases(id),
        chunk_index INTEGER NOT NULL,
        content     TEXT NOT NULL,
        chroma_id   TEXT NOT NULL UNIQUE,
        created_at  TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_chunk_doc_id ON chunks(doc_id);",
    "CREATE INDEX IF NOT EXISTS idx_chunk_kb_id ON chunks(kb_id);",
    "CREATE INDEX IF NOT EXISTS idx_chunk_chroma_id ON chunks(chroma_id);",
    """
    CREATE TABLE IF NOT EXISTS model_configs (
        id           TEXT PRIMARY KEY,
        model_type   TEXT NOT NULL,
        model_name   TEXT NOT NULL,
        api_base_url TEXT NOT NULL,
        api_key      TEXT DEFAULT '',
        dimension    INTEGER DEFAULT NULL,
        is_active    INTEGER DEFAULT 1,
        created_at   TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_model_type ON model_configs(model_type);",
    "CREATE INDEX IF NOT EXISTS idx_model_active ON model_configs(is_active);",
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id          TEXT PRIMARY KEY,
        session_id  TEXT NOT NULL,
        kb_id       TEXT REFERENCES knowledge_bases(id) ON DELETE CASCADE,
        role        TEXT NOT NULL,
        content     TEXT NOT NULL,
        "references" TEXT DEFAULT NULL,
        created_at  TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_conv_session_id ON conversations(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_conv_session_created ON conversations(session_id, created_at);",
]

# --- 插入默认角色和管理员 ---
SEED_SQL = [
    """
    INSERT OR IGNORE INTO roles (id, name, description, permissions, created_at)
    VALUES
        ('r001', '管理员', '系统管理员，拥有全部权限', '["kb:create","kb:delete","doc:upload","doc:delete","rag:test","chat:send"]', datetime('now')),
        ('r002', '编辑员', '可管理知识库和文档',         '["kb:create","doc:upload","rag:test"]',                        datetime('now')),
        ('r003', '访客',   '仅可查看和检索',             '["rag:test","chat:send"]',                                    datetime('now'));
    """,
    """
    INSERT OR IGNORE INTO users (id, username, password_hash, display_name, role_id, status, created_at)
    VALUES ('u001', 'admin', '$2b$12$LJ3m4ys3GZfnYMz8kVsKaOCG4.5Qh8rYFJR6vJb5JNqLmR9f7Xh3e', '管理员', 'r001', 'active', datetime('now'));
    """,
    """
    INSERT OR IGNORE INTO model_configs (id, model_type, model_name, api_base_url, is_active, created_at)
    VALUES
        ('m001', 'llm',       'gpt-4o-mini',             'https://api.openai.com/v1', 1, datetime('now')),
        ('m002', 'embedding', 'text-embedding-3-small',   'https://api.openai.com/v1', 1, datetime('now'));
    """,
]

# --- 执行建表 ---
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("[init_db] 创建数据表...")
for sql in SQL_STATEMENTS:
    try:
        cursor.execute(sql)
    except sqlite3.Error as e:
        print(f"  ! 警告: {e}")

print("[init_db] 写入种子数据...")
for sql in SEED_SQL:
    try:
        cursor.execute(sql)
    except sqlite3.Error as e:
        print(f"  ! 警告: {e}")

conn.commit()
conn.close()

# --- 验证 ---
print(f"[init_db] 验证数据库...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"  已创建 {len(tables)} 张表: {', '.join(t[0] for t in tables)}")
roles_count = cursor.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
users_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
print(f"  种子数据: {roles_count} 个角色, {users_count} 个用户")
conn.close()

print("[init_db] 数据库初始化完成！")
print(f"[init_db] 默认管理员账号: admin / admin123")
