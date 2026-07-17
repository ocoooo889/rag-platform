# 智能 RAG 平台 — 数据库表设计

> 版本：v1.0 | 负责人：6号 | 更新日期：2026-07-15
>
> 数据库：SQLite（每人独立文件 `dev_{姓名}_rag.db`）
> ORM：SQLAlchemy

---

## 一、实体关系图（ER）

```
┌─────────────┐       ┌────────────────┐
│    Roles     │       │     Users      │
│─────────────│       │────────────────│
│ id (PK)     │←──────│ role_id (FK)   │
│ name        │  1:N  │ id (PK)        │
│ description │       │ username       │
│ permissions │       │ password_hash  │
│ created_at  │       │ display_name   │
└─────────────┘       │ status         │
                      │ created_at     │
                      └───────┬────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
         ┌──────────────────┐  ┌──────────────────────┐
         │ KnowledgeBases   │  │    ModelConfigs      │
         │──────────────────│  │──────────────────────│
         │ id (PK)          │  │ id (PK)              │
         │ name             │  │ model_type           │
         │ description      │  │ model_name           │
         │ created_by (FK)  │  │ api_base_url         │
         │ created_at       │  │ dimension (embed)    │
         └────────┬─────────┘  │ is_active            │
                  │            │ created_at           │
                  │            └──────────────────────┘
                  │
         ┌────────┴─────────┐
         │   Documents      │
         │──────────────────│
         │ id (PK)          │
         │ kb_id (FK)       │
         │ filename         │
         │ file_type        │
         │ file_size        │
         │ file_path        │
         │ status           │
         │ chunk_count      │
         │ uploaded_by (FK) │
         │ uploaded_at      │
         └────────┬─────────┘
                  │
         ┌────────┴─────────┐
         │   Chunks         │  ← 仅 SQLite 记录 meta
         │──────────────────│    实际向量在 Chroma
         │ id (PK)          │
         │ doc_id (FK)      │
         │ kb_id (FK)       │
         │ chunk_index      │
         │ content          │
         │ chroma_id        │
         │ created_at       │
         └──────────────────┘

         ┌──────────────────┐
         │  Conversations   │  ← 多轮对话历史
         │──────────────────│
         │ id (PK)          │
         │ session_id       │
         │ kb_id (FK)       │
         │ role             │
         │ content          │
         │ references       │
         │ created_at       │
         └──────────────────┘
```

---

## 二、表结构详述

### 2.1 `roles` — 角色表

| 字段 | 类型 | 约束 | 说明 |
|------|------|:----:|------|
| `id` | TEXT | PK, UUID | 角色唯一标识，如 `r001` |
| `name` | TEXT | NOT NULL, UNIQUE | 角色名称，如 "管理员" |
| `description` | TEXT | DEFAULT '' | 角色描述 |
| `permissions` | TEXT | DEFAULT '[]' | 权限列表（JSON 数组字符串） |
| `created_at` | TEXT | NOT NULL | ISO 8601 时间戳 |

**索引：**
- `idx_roles_name` ON `name`

**权限枚举值：**
```json
["kb:create", "kb:delete", "doc:upload", "doc:delete", "rag:test", "chat:send"]
```

---

### 2.2 `users` — 用户表

| 字段 | 类型 | 约束 | 说明 |
|------|------|:----:|------|
| `id` | TEXT | PK, UUID | 用户唯一标识，如 `u001` |
| `username` | TEXT | NOT NULL, UNIQUE | 登录用户名 |
| `password_hash` | TEXT | NOT NULL | BCrypt 加密后的密码 |
| `display_name` | TEXT | NOT NULL | 显示名称 |
| `role_id` | TEXT | FK → roles.id | 关联角色 |
| `status` | TEXT | NOT NULL, DEFAULT 'active' | 状态：`active` / `disabled` |
| `created_at` | TEXT | NOT NULL | ISO 8601 时间戳 |

**索引：**
- `idx_users_username` ON `username`
- `idx_users_role_id` ON `role_id`

**外键：**
- `role_id` → `roles(id)` ON DELETE RESTRICT（不允许删除有用户的角色）

---

### 2.3 `knowledge_bases` — 知识库表

| 字段 | 类型 | 约束 | 说明 |
|------|------|:----:|------|
| `id` | TEXT | PK, UUID | 知识库唯一标识，如 `kb001` |
| `name` | TEXT | NOT NULL, UNIQUE | 知识库名称 |
| `description` | TEXT | DEFAULT '' | 知识库描述 |
| `created_by` | TEXT | FK → users(id) | 创建人 |
| `created_at` | TEXT | NOT NULL | ISO 8601 时间戳 |

**索引：**
- `idx_kb_name` ON `name`
- `idx_kb_created_by` ON `created_by`

---

### 2.4 `documents` — 文档表

| 字段 | 类型 | 约束 | 说明 |
|------|------|:----:|------|
| `id` | TEXT | PK, UUID | 文档唯一标识，如 `doc001` |
| `kb_id` | TEXT | FK → knowledge_bases(id), NOT NULL | 所属知识库 |
| `filename` | TEXT | NOT NULL | 原始文件名 |
| `file_type` | TEXT | NOT NULL | 文件类型：`md` / `txt` |
| `file_size` | INTEGER | NOT NULL | 文件字节数 |
| `file_path` | TEXT | NOT NULL | 服务器存储路径 |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' | 处理状态：`pending` / `processing` / `completed` / `failed` |
| `chunk_count` | INTEGER | DEFAULT 0 | 切片数量 |
| `uploaded_by` | TEXT | FK → users(id) | 上传人 |
| `uploaded_at` | TEXT | NOT NULL | ISO 8601 时间戳 |

**索引：**
- `idx_doc_kb_id` ON `kb_id`
- `idx_doc_status` ON `status`
- `idx_doc_kb_status` ON `kb_id, status`（复合索引）

**外键：**
- `kb_id` → `knowledge_bases(id)` ON DELETE CASCADE（删除知识库时级联删除文档）

---

### 2.5 `chunks` — 文本分片表（SQLite 元数据记录）

> 说明：此表仅记录分片的元数据（文本内容和关联信息），**实际向量存储在 Chroma 向量库中**。Chroma 中每条向量的 `id` 字段与此表的 `chroma_id` 对应。

| 字段 | 类型 | 约束 | 说明 |
|------|------|:----:|------|
| `id` | TEXT | PK, UUID | 分片唯一标识，如 `c001` |
| `doc_id` | TEXT | FK → documents(id), NOT NULL | 所属文档 |
| `kb_id` | TEXT | FK → knowledge_bases(id), NOT NULL | 所属知识库（冗余，方便跨文档检索过滤） |
| `chunk_index` | INTEGER | NOT NULL | 分片在文档内的序号（从 0 开始） |
| `content` | TEXT | NOT NULL | 分片文本内容（约 500 字） |
| `chroma_id` | TEXT | NOT NULL, UNIQUE | Chroma 向量库中对应的 ID |
| `created_at` | TEXT | NOT NULL | ISO 8601 时间戳 |

**索引：**
- `idx_chunk_doc_id` ON `doc_id`
- `idx_chunk_kb_id` ON `kb_id`
- `idx_chunk_chroma_id` ON `chroma_id`

**外键：**
- `doc_id` → `documents(id)` ON DELETE CASCADE（删除文档时级联删除分片记录）

---

### 2.6 `conversations` — 对话历史表

> 说明：多轮对话功能的核心存储。每次对话请求的 user 消息和 assistant 回复各记录一条，通过 `session_id` 关联同一会话窗口。按 `created_at` 排序即可还原完整对话时序。

| 字段 | 类型 | 约束 | 说明 |
|------|------|:----:|------|
| `id` | TEXT | PK, UUID | 消息唯一标识 |
| `session_id` | TEXT | NOT NULL | 会话标识，同一会话窗口内不变 |
| `kb_id` | TEXT | FK → knowledge_bases(id) | 所属知识库 |
| `role` | TEXT | NOT NULL | 角色：`user` / `assistant` |
| `content` | TEXT | NOT NULL | 消息正文 |
| `references` | TEXT | DEFAULT NULL | JSON 字符串，仅 `assistant` 消息存储引用来源 |
| `created_at` | TEXT | NOT NULL | ISO 8601 时间戳 |

**索引：**
- `idx_conv_session_id` ON `session_id`
- `idx_conv_session_created` ON `session_id, created_at`

**外键：**
- `kb_id` → `knowledge_bases(id)` ON DELETE CASCADE（删除知识库时级联删除对话历史）

**session_id 兜底行为：**
- 若前端传入的 `session_id` 在表中无记录 → 不报错，视为新会话，正常处理
- 若请求中未传 `session_id` → 后端生成新 UUID 作为 `session_id`，并在响应中返回

---

### 2.7 `model_configs` — 大模型配置表

| 字段 | 类型 | 约束 | 说明 |
|------|------|:----:|------|
| `id` | TEXT | PK, UUID | 配置唯一标识，如 `m001` |
| `model_type` | TEXT | NOT NULL | 模型类型：`llm` / `embedding` |
| `model_name` | TEXT | NOT NULL | 模型名称，如 `gpt-4o-mini` |
| `api_base_url` | TEXT | NOT NULL | API 基础地址 |
| `api_key` | TEXT | DEFAULT '' | API Key（本次迭代从 .env 读取，此字段留空） |
| `dimension` | INTEGER | DEFAULT NULL | Embedding 向量维度（仅 `embedding` 类型有值，默认为 1536） |
| `is_active` | INTEGER | DEFAULT 1 | 是否启用：1 启用 / 0 停用 |
| `created_at` | TEXT | NOT NULL | ISO 8601 时间戳 |

**索引：**
- `idx_model_type` ON `model_type`
- `idx_model_active` ON `is_active`

---

## 三、CREATE TABLE SQL（一键执行）

```sql
CREATE TABLE IF NOT EXISTS roles (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    permissions TEXT DEFAULT '[]',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    role_id       TEXT REFERENCES roles(id) ON DELETE RESTRICT,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);

CREATE TABLE IF NOT EXISTS knowledge_bases (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    created_by  TEXT REFERENCES users(id),
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_kb_name ON knowledge_bases(name);
CREATE INDEX IF NOT EXISTS idx_kb_created_by ON knowledge_bases(created_by);

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
CREATE INDEX IF NOT EXISTS idx_doc_kb_id ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_doc_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_doc_kb_status ON documents(kb_id, status);

CREATE TABLE IF NOT EXISTS chunks (
    id          TEXT PRIMARY KEY,
    doc_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kb_id       TEXT NOT NULL REFERENCES knowledge_bases(id),
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    chroma_id   TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunk_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunk_kb_id ON chunks(kb_id);
CREATE INDEX IF NOT EXISTS idx_chunk_chroma_id ON chunks(chroma_id);

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
CREATE INDEX IF NOT EXISTS idx_model_type ON model_configs(model_type);
CREATE INDEX IF NOT EXISTS idx_model_active ON model_configs(is_active);

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    kb_id      TEXT REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    references TEXT DEFAULT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_session_created ON conversations(session_id, created_at);
```

---

## 四、约束与级联策略总结

| 操作 | 行为 |
|------|------|
| 删除角色（有用户关联） | `ON DELETE RESTRICT` — 拒绝删除，返回 400 提示 |
| 删除知识库 | `ON DELETE CASCADE` — 级联删除其下所有文档 + 分片记录 |
| 删除文档 | `ON DELETE CASCADE` — 级联删除其下所有分片记录 |
| 删除知识库 | `ON DELETE CASCADE` — 级联删除其下对话历史 |
| 删除用户 | 无级联约束 — 仅置 `status=disabled` 逻辑删除 |

> Chroma 向量库中的向量数据需在应用层同步清理（文档删除时同步调用 Chroma 的 `delete` 方法）。
