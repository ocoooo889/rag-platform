# 智能 RAG 平台 — API 接口契约

> ⚠️ **优先级声明**：本文件为项目唯一接口契约标准。方案文档中的 JSON 示例仅为示意，前后端开发以本文件为准。

> 版本：v1.0 | 负责人：6号 | 更新日期：2026-07-15
>
> 所有接口统一前缀 `/api`，所有返回体遵守统一格式，供前后端并行开发用。

---

## 一、统一返回格式与异常码

### 1.1 统一返回体

**成功返回：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

**异常返回：**
```json
{
  "code": 400,
  "msg": "详细错误描述",
  "data": null
}
```

### 1.2 异常码规范

| code | 含义 | 触发场景 |
|:--:|------|------|
| 0 | 成功 | 所有正常返回 |
| 400 | 参数错误 | 必填字段为空、格式校验失败 |
| 401 | 未登录 / Token 失效 | 未携带 Token 或 Token 过期 |
| 403 | 权限不足 | 无权限访问该接口 |
| 404 | 资源不存在 | 知识库 / 文档 ID 不存在 |
| 4001 | 用户组未授权 | 用户不在任何用户组，或组未分配知识库（后端 B） |
| 4002 | 文档未就绪 | 文档为 pending/processing/failed，不可检索/对话 |
| 4003 | 白标配置缺失 | 系统品牌配置未初始化，使用默认值兜底 |
| 4004 | 向量不可用 | 文档 status=degraded 时禁止纯向量检索，请用关键词/混合或重新向量化 |
| 500 | 服务内部异常 | 未预期的服务器错误 |
| 5001 | 向量库异常 | Chroma 连接失败 / 查询失败 |
| 5002 | 大模型调用异常 | LLM API 超时 / Key 失效 / 返回异常 |

### 1.3 通用请求头

| Header | 必填 | 说明 |
|--------|:----:|------|
| `Authorization` | 是 | `Bearer {jwt_token}`，登录接口除外 |
| `Content-Type` | 是 | `application/json` |

### 1.4 通用分页请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|:----:|:----:|------|
| `page` | int | 否 | 1 | 页码，从 1 开始 |
| `page_size` | int | 否 | 10 | 每页条数，最多 100 |

### 1.5 通用分页响应结构

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 10
  }
}
```

---

## 二、鉴权接口（4号 · 后端 B）

### POST `/api/auth/login`

登录鉴权，返回 JWT Token。

**请求体：**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**成功响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "u001",
      "username": "admin",
      "role_name": "管理员"
    }
  }
}
```

**异常：** 401 — 用户名或密码错误

---

### POST `/api/auth/register`

用户注册（Day1 可暂不实现，管理员后台直接添加）。

**请求体：**
```json
{
  "username": "zhangsan",
  "password": "pass123",
  "display_name": "张三",
  "role_id": "r001"
}
```

**成功响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": { "user_id": "u002" }
}
```

---

## 三、用户管理接口（4号 · 后端 B）

### GET `/api/users` — 用户列表（分页 + 可搜索）

**查询参数：** `?page=1&page_size=10&keyword=张三`

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "u001",
        "username": "admin",
        "display_name": "管理员",
        "role_id": "r001",
        "role_name": "管理员",
        "status": "active",
        "created_at": "2026-07-15T09:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

### POST `/api/users` — 新增用户

**请求体：**
```json
{
  "username": "lisi",
  "password": "pass456",
  "display_name": "李四",
  "role_id": "r002",
  "status": "active"
}
```

**响应：** `{"code":0,"msg":"success","data":{"user_id":"u003"}}`

### PUT `/api/users/{user_id}` — 编辑用户

**请求体：** 同 POST，字段全量更新

**响应：** `{"code":0,"msg":"success","data":null}`

### DELETE `/api/users/{user_id}` — 删除用户

**响应：** `{"code":0,"msg":"success","data":null}`

**异常：** 404 — 用户不存在

---

## 四、角色管理接口（4号 · 后端 B）

### GET `/api/roles` — 角色列表

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "id": "r001",
      "name": "管理员",
      "description": "系统管理员，拥有全部权限",
      "permissions": ["kb:create","kb:delete","doc:upload","doc:delete","rag:test","chat:send"],
      "created_at": "2026-07-15T09:00:00"
    }
  ]
}
```

### POST `/api/roles` — 新增角色

**请求体：**
```json
{
  "name": "编辑员",
  "description": "可管理知识库和文档",
  "permissions": ["kb:create","doc:upload","rag:test"]
}
```

### PUT `/api/roles/{role_id}` — 编辑角色

**请求体：** 同 POST

### DELETE `/api/roles/{role_id}` — 删除角色

**异常：** 400 — 该角色下有未删除的用户，无法删除

---

## 五、知识库管理接口（4号 · 后端 B）

### GET `/api/knowledge-bases` — 知识库列表（分页）

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "kb001",
        "name": "公司制度知识库",
        "description": "存放公司内部制度文档",
        "doc_count": 5,
        "chunk_count": 120,
        "created_at": "2026-07-15T09:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

### POST `/api/knowledge-bases` — 新增知识库

**请求体：**
```json
{
  "name": "公司制度知识库",
  "description": "存放公司内部制度文档"
}
```

**响应：** `{"code":0,"msg":"success","data":{"kb_id":"kb002"}}`

### PUT `/api/knowledge-bases/{kb_id}` — 编辑知识库

### DELETE `/api/knowledge-bases/{kb_id}` — 删除知识库（级联删除其下所有文档 + 向量）

**警告：** 删除知识库会同时删除该知识库下所有文档及其向量数据，不可恢复

---

## 六、文档管理接口（4号 · 后端 B）

### GET `/api/knowledge-bases/{kb_id}/documents` — 文档列表（按知识库筛选）

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "doc001",
        "kb_id": "kb001",
        "filename": "公司考勤制度.md",
        "file_type": "md",
        "file_size": 15230,
        "chunk_count": 30,
        "status": "completed",
        "uploaded_at": "2026-07-15T09:05:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

**文档状态枚举：**

| status | 含义 |
|--------|------|
| pending | 已上传，等待处理 |
| processing | 正在切片 + 向量化 |
| completed | 向量 + BM25 均就绪，可检索 |
| degraded | 仅 BM25 就绪（向量写入失败）；可关键词/混合，不可纯向量 |
| failed | 处理失败 |

### POST `/api/documents/{doc_id}/reprocess` — 重新向量化

具备该文档所属知识库访问权即可。清理旧切片/向量后后台重新入库。

**异常：**
- 404 — 文档或原始文件不存在
- 400 — 正在处理中（`processing` 且 `updated_at` 未超过 10 分钟）

### POST `/api/knowledge-bases/{kb_id}/documents/upload` — 上传文档

**请求格式：** `multipart/form-data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `file` | File | 是 | 仅支持 .md / .txt，最大 10MB |

**成功响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "doc_id": "doc002",
    "filename": "新文档.md",
    "status": "pending"
  }
}
```

**异常：** 400 — 文件格式不支持 / 超出大小限制

### DELETE `/api/knowledge-bases/{kb_id}/documents/{doc_id}` — 删除文档（同步清理向量）

**响应：** `{"code":0,"msg":"success","data":null}`

### GET `/api/documents/all` — 全部文档列表（不带知识库筛选，用于级联下拉）

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "doc_id": "doc001",
      "kb_id": "kb001",
      "filename": "公司考勤制度.md"
    }
  ]
}
```

---

## 七、大模型管理接口（4号 · 后端 B · 本次迭代 UI 保留数据写死 .env）

### GET `/api/models` — 模型配置列表

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "id": "m001",
      "model_type": "llm",
      "model_name": "gpt-4o-mini",
      "api_base_url": "https://api.openai.com/v1",
      "is_active": true
    },
    {
      "id": "m002",
      "model_type": "embedding",
      "model_name": "text-embedding-3-small",
      "dimension": 1536,
      "api_base_url": "https://api.openai.com/v1",
      "is_active": true
    }
  ]
}
```

> Day1 本次迭代数据从 `.env` 读取，页面不做编辑功能。

### POST `/api/models` — 新增模型配置（留空壳）

### PUT `/api/models/{model_id}` — 编辑模型配置（留空壳）

### DELETE `/api/models/{model_id}` — 删除模型配置（留空壳）

---

## 八、命中率测试接口（3号 · 后端 A · 核心 P0）

### POST `/api/rag/test_retrieve`

**请求体：**
```json
{
  "kb_id": "kb001",
  "doc_id": "doc001",
  "search_type": "hybrid",
  "query": "公司年假有几天？",
  "top_n": 3
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `kb_id` | string | 是 | 知识库 ID |
| `doc_id` | string | 是 | 文档 ID |
| `search_type` | string | 是 | 枚举值：`vector` / `keyword` / `hybrid` |
| `query` | string | 是 | 测试问题，不能为空 |
| `top_n` | int | 否 | 返回命中条数，默认 3，最大 10 |

**成功响应（有命中结果）：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "search_type": "hybrid",
    "total_hits": 2,
    "hits": [
      {
        "chunk_id": "c001",
        "content": "根据公司规定，工作满一年的员工可享受 5 天年假...",
        "score": 0.86,
        "source_doc": "公司考勤制度.md",
        "doc_id": "doc001"
      },
      {
        "chunk_id": "c002",
        "content": "年假应在当年 12 月 31 日前使用完毕...",
        "score": 0.72,
        "source_doc": "公司考勤制度.md",
        "doc_id": "doc001"
      }
    ]
  }
}
```

**成功响应（无命中）：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "search_type": "vector",
    "total_hits": 0,
    "hits": []
  }
}
```

**异常：**
- 400 — 必填参数为空
- 404 — 知识库 / 文档不存在
- 4002 — 文档未就绪（pending/processing/failed）
- 4004 — 文档 degraded，禁止纯向量检索
- 5001 — 向量库异常（Chroma 连接失败）

---

## 九、智能对话接口（3号 · 后端 A · 核心 P0）

### POST `/api/chat/send`

**请求体：**
```json
{
  "kb_id": "kb001",
  "query": "公司年假怎么申请？",
  "session_id": "s001",
  "search_type": "hybrid",
  "top_n": 3
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `kb_id` | string | 是 | 知识库 ID |
| `query` | string | 是 | 用户问题 |
| `session_id` | string | 否 | 会话标识。不传则新建会话并返回新 session_id；传入已有 session_id 则加载历史实现多轮对话。若传入的 session_id 在库中无记录，不做报错，视为新会话继续处理 |
| `search_type` | string | 否 | 默认 `hybrid` |
| `top_n` | int | 否 | 检索上下文条数，默认 3 |

**成功响应（流式模式）：**
```
Content-Type: text/event-stream

data: {"type": "start", "session_id": "s001"}
data: {"type": "chunk", "content": "根据"}
data: {"type": "chunk", "content": "公司考勤制度"}
data: {"type": "chunk", "content": "..."}
data: {"type": "done", "content": "", "references": [{"chunk_id":"c001","content":"引用原文...","score":0.86}]}
```

**成功响应（非流式模式）：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "session_id": "s001",
    "answer": "根据公司考勤制度，工作满一年的员工可享受 5 天年假...",
    "references": [
      {
        "chunk_id": "c001",
        "content": "根据公司规定，工作满一年的员工可享受 5 天年假...",
        "score": 0.86,
        "source_doc": "公司考勤制度.md"
      }
    ]
  }
}
```

**异常：**
- 400 — 必填参数为空
- 5002 — 大模型调用异常（LLM API 超时 / Key 失效）

### POST `/api/chat/stream` — 流式 SSE 版本（推荐）

请求体同 `/api/chat/send`，支持 `session_id` 多轮对话，返回 SSE 流（同上流式模式）。

### GET `/api/chat/sessions` — 会话列表（可选）

**查询参数：** `?kb_id=kb001&page=1&page_size=20`

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      {
        "session_id": "s001",
        "title": "公司年假怎么申请？",
        "last_message": "根据公司考勤制度...",
        "updated_at": "2026-07-15T14:30:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

### GET `/api/chat/sessions/{session_id}/messages` — 会话消息历史

**查询参数：** `?page=1&page_size=50`

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "msg001",
        "role": "user",
        "content": "公司年假有几天？",
        "created_at": "2026-07-15T14:25:00"
      },
      {
        "id": "msg002",
        "role": "assistant",
        "content": "根据公司考勤制度，工作满一年的员工可享受 5 天年假...",
        "references": [{"chunk_id":"c001","content":"...","score":0.86}],
        "created_at": "2026-07-15T14:25:05"
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 50
  }
}
```

### DELETE `/api/chat/sessions/{session_id}` — 删除会话（级联删除消息）

**响应：** `{"code":0,"msg":"success","data":null}`

---

## 十、系统概览接口（4号 · 后端 B）

### GET `/api/dashboard/stats`

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "kb_count": 5,
    "doc_count": 12,
    "chunk_count": 350,
    "call_count": null
  }
}
```

> `call_count` 本次迭代为 null（统计留空壳，二期实现）

---

## 十一、接口列表速查表

| 方法 | 路径 | 负责人 | 说明 |
|------|------|:------:|------|
| POST | `/api/auth/login` | 4号 | 登录 |
| POST | `/api/auth/register` | 4号 | 注册 |
| GET | `/api/users` | 4号 | 用户列表 |
| POST | `/api/users` | 4号 | 新增用户 |
| PUT | `/api/users/{user_id}` | 4号 | 编辑用户 |
| DELETE | `/api/users/{user_id}` | 4号 | 删除用户 |
| GET | `/api/roles` | 4号 | 角色列表 |
| POST | `/api/roles` | 4号 | 新增角色 |
| PUT | `/api/roles/{role_id}` | 4号 | 编辑角色 |
| DELETE | `/api/roles/{role_id}` | 4号 | 删除角色 |
| GET | `/api/knowledge-bases` | 4号 | 知识库列表 |
| POST | `/api/knowledge-bases` | 4号 | 新增知识库 |
| PUT | `/api/knowledge-bases/{kb_id}` | 4号 | 编辑知识库 |
| DELETE | `/api/knowledge-bases/{kb_id}` | 4号 | 删除知识库 |
| GET | `/api/knowledge-bases/{kb_id}/documents` | 4号 | 文档列表 |
| POST | `/api/knowledge-bases/{kb_id}/documents/upload` | 4号 | 上传文档 |
| POST | `/api/documents/{doc_id}/reprocess` | 4号 | 重新向量化 |
| DELETE | `/api/knowledge-bases/{kb_id}/documents/{doc_id}` | 4号 | 删除文档 |
| GET | `/api/documents/all` | 4号 | 全部文档（级联下拉用） |
| GET | `/api/models` | 4号 | 模型列表 |
| POST | `/api/models` | 4号 | 新增模型（留空壳） |
| PUT | `/api/models/{model_id}` | 4号 | 编辑模型（留空壳） |
| DELETE | `/api/models/{model_id}` | 4号 | 删除模型（留空壳） |
| GET | `/api/dashboard/stats` | 4号 | 系统概览统计 |
| POST | `/api/rag/test_retrieve` | 3号 | 命中率测试 |
| POST | `/api/chat/send` | 3号 | 智能对话 |
| POST | `/api/chat/stream` | 3号 | 智能对话（流式） |
| GET | `/api/chat/sessions` | 3号 | 会话列表 |
| GET | `/api/chat/sessions/{session_id}/messages` | 3号 | 会话消息历史 |
| DELETE | `/api/chat/sessions/{session_id}` | 3号 | 删除会话 |
