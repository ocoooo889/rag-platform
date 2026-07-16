# 智能对话接口 + 命中率测试接口 — V2 测试报告

> **测试基准**：`RAG项目完整管控方案-V2.md`
> **测试范围**：`chat.py`（`POST /api/chat/send` + `POST /api/chat/stream`）、`rag.py`（`POST /api/rag/test_retrieve`）
> **测试日期**：2026-07-16
> **测试工程师**：5号
> **版本**：v1.0

---

## 一、静态代码审查 — 对照 V2 方案发现的问题

### 🔴 P0 阻塞级：权限校验缺失（两个接口都有）

**V2 方案要求（第七章 7.4 节）**：

| 接口 | V2 要求 |
|------|------|
| `POST /api/rag/test_retrieve` | **先校验 KB + 文档权限，再检索** |
| `POST /api/chat/send` | **先校验 KB 权限，再对话** |

**实际代码现状**：

```python
# chat.py — 没有任何鉴权依赖
@router.post("/send")
async def chat_send(req: ChatRequest):  # ❌ 缺少 user=Depends(get_current_user)
    ...
    # ❌ 没有 require_kb_access(req.kb_id) 调用

# rag.py — 同样没有鉴权
@router.post("/test_retrieve")
async def test_retrieve(req: HitTestRequest):  # ❌ 缺少 user=Depends(get_current_user)
    ...
    # ❌ 没有 require_kb_access(req.kb_id) 调用
```

**影响**：任何未登录用户都可以直接调用这两个接口。V2 的核心安全需求——用户组权限隔离（跨组访问返回 403、未分配用户组返回 4001）——在后端 A 的两个接口中**完全没有落地**。这是 V2 方案 P0 必保项，属于阻塞级 bug。

---

### 🔴 P0 阻塞级：V2 新增 4 张表未建表

**V2 方案要求（第七章 7.1 节）**：新增 `user_groups`、`user_group_members`、`kb_group_access`、`system_config` 四张表。

**`init_db.py` 实际建表**：roles、users、knowledge_bases、documents、chunks、model_configs、conversations — **只有 7 张表，缺少 4 张 V2 表**。

**影响**：权限中间件 `require_kb_access()` 无法查询 `kb_group_access` 表，白标配置 `GET /api/system/branding` 无法读取 `system_config` 表。整个 V2 权限和白标体系无法运行。

---

### 🔴 P0 阻塞级：`config.py` 缺少 V2 配置项

**V2 方案要求（第四章 4.1 节 + 第八章）**：

```python
# config.py 中缺失：
LANGFUSE_PUBLIC_KEY   # ❌ 未定义
LANGFUSE_SECRET_KEY   # ❌ 未定义
LANGFUSE_HOST         # ❌ 未定义
PROMETHEUS_ENABLED    # ❌ 未定义
METRICS_PATH          # ❌ 未定义
```

**影响**：`langfuse_tracer.py` 中 `new_request_id()` 能正常生成 UUID，但 Langfuse SDK 初始化会因为缺少配置而失败。Prometheus `/metrics` 端点也无法启用。

---

### 🟡 P1 严重：对话接口响应缺少 `query` 字段

**V2 方案契约（第十五章 15.2 节）**：

```json
{
  "code": 0,
  "data": {
    "answer": "...",
    "query": "用户原始提问",
    "session_id": "...",
    "references": [...]
  }
}
```

**实际代码返回**：

```python
return ok({
    "session_id": session_id,
    "answer": answer,
    "references": refs,
    "request_id": request_id,
    # ❌ 缺少 "query"
})
```

**影响**：前端如果需要回显用户原始问题，只能从请求侧保留，契约不一致。

---

### 🟡 P1 严重：LLM 异常检测依赖字符串匹配

```python
# chat.py  Line 58-59
if isinstance(answer, str) and answer.startswith("大模型服务暂时不可用"):
    return fail(5002, answer)
```

**问题**：`LLMClient.chat()` 在超时/异常时返回的字符串与这里硬编码的匹配。如果 `LLMClient` 的文案被修改、或者 LLM 真的返回了以这句话开头的内容，都会误判。应该用异常机制（raise `LLMServiceError`）而不是字符串匹配。

---

### 🟡 P1 严重：`chat.py` 缺少 `search_type` 校验

`rag.py` 中对 `search_type` 做了严格校验：

```python
# rag.py — 有校验 ✅
if search_type not in {"vector", "keyword", "hybrid"}:
    return fail(400, "search_type 必须是 vector / keyword / hybrid")
```

`chat.py` 中只有默认值，没有校验：

```python
# chat.py — 无校验 ❌
search_type=req.search_type or "hybrid",
```

如果传入 `search_type: "invalid"`，会直接传给 `RAGPipeline.query()`，下游行为不确定。

---

### 🟡 P1 严重：`init_db.py` 缺少 V2 种子数据

V2 方案 17.1 清单第 15 条要求："预置 system_config 表默认品牌数据 + 初始化一个 admin 用户组"。当前的 `SEED_SQL` 中没有这些。

---

### 🟢 P2 一般：`top_n` 参数无边界校验

两个接口都没有对 `top_n` 做范围校验（如 1~20），传入 0 或负数可能导致异常。

---

### 🟢 P2 一般：流式接口断连时对话不保存

```python
# chat.py stream endpoint
async def event_gen():
    ...
    full = ""
    async for token in token_iter:
        full += token
        ...
    # save_conversation 在生成器内部，如果客户端断连，生成器可能提前终止
    save_conversation(...)
```

如果客户端在 SSE 流中途断开连接，`save_conversation` 可能不会执行，导致对话记录丢失。

---

## 二、测试用例

### 2.1 智能对话接口 — `POST /api/chat/send`

#### 参数校验

| 编号 | 场景 | 请求 | 预期结果 |
|:--:|------|------|------|
| CHAT-01 | kb_id 为空 | `{"kb_id":"", "query":"test"}` | `code: 400, msg: "缺少必填参数: kb_id"` |
| CHAT-02 | kb_id 缺失 | `{"query":"test"}` | `code: 400, msg: "缺少必填参数: kb_id"` |
| CHAT-03 | query 为空 | `{"kb_id":"kb1", "query":""}` | `code: 400, msg: "缺少必填参数: query"` |
| CHAT-04 | query 缺失 | `{"kb_id":"kb1"}` | `code: 400, msg: "缺少必填参数: query"` |
| CHAT-05 | kb_id 不存在 | `{"kb_id":"nonexistent", "query":"test"}` | `code: 404, msg: "知识库不存在"` |
| CHAT-06 | search_type 非法值 | `{"kb_id":"kb1", "query":"test", "search_type":"invalid"}` | **当前行为：不校验，直接传给下游**。建议返回 `code: 400` |
| CHAT-07 | top_n = 0 | `{"kb_id":"kb1", "query":"test", "top_n":0}` | **当前行为：不校验**。建议返回 `code: 400` |
| CHAT-08 | top_n = -1 | `{"kb_id":"kb1", "query":"test", "top_n":-1}` | **当前行为：不校验**。建议返回 `code: 400` |
| CHAT-09 | 仅传必填参数 | `{"kb_id":"kb1", "query":"test"}` | `code: 0`，`search_type` 默认 `hybrid`，`session_id` 自动生成 |

#### 文档准入 4002（V2 第十一章）

| 编号 | 场景 | 前置条件 | 预期结果 |
|:--:|------|------|------|
| CHAT-10 | 知识库无文档 | KB 下文档数为 0 | `code: 404, msg: "该知识库下暂无可用文档"` |
| CHAT-11 | 全部文档 pending | KB 下有 3 篇文档，全部 status=pending | `code: 4002, msg: "知识库下 3 篇文档正在处理中，请等待处理完成后再试"` |
| CHAT-12 | 全部文档 processing | KB 下 2 篇文档，全部 status=processing | `code: 4002` |
| CHAT-13 | 全部文档 failed | KB 下 1 篇文档，status=failed | `code: 4002`（failed 也是非 completed） |
| CHAT-14 | 部分 completed + 部分 pending | KB 下 2 篇 completed + 1 篇 pending | `code: 0`（放行，检索层只取 completed 的 chunks） |
| CHAT-15 | 全部 completed | KB 下全部文档 completed | `code: 0`，正常对话 |

#### 多轮对话

| 编号 | 场景 | 前置条件 | 预期结果 |
|:--:|------|------|------|
| CHAT-16 | 首轮对话（无 session_id） | 不传 session_id | 自动生成 `session_id` 返回，对话历史为空 |
| CHAT-17 | 多轮对话 | 传入已有 session_id | 携带历史上下文，`MAX_CHAT_HISTORY_ROUNDS=10` |
| CHAT-18 | 超长历史截断 | 对话超过 10 轮 | 仅保留最近 10 轮，早期消息被截断 |

#### 正常返回

| 编号 | 场景 | 预期结果 |
|:--:|------|------|
| CHAT-19 | 正常问答 | `code: 0`，`data.answer` 非空，`data.references` 包含检索到的 chunk |
| CHAT-20 | 知识库无相关答案 | `answer` 包含"未查询到相关内容"等兜底文案 |
| CHAT-21 | 返回字段完整性 | `data` 包含 `session_id`, `answer`, `references`, `request_id` |
| CHAT-22 | ⚠️ 契约对齐 | **V2 契约要求返回 `query` 字段，当前代码未返回**（见 BUG-04） |

#### 降级/异常

| 编号 | 场景 | 前置条件 | 预期结果 |
|:--:|------|------|------|
| CHAT-23 | LLM 超时 | LLM API 超时 | `code: 5002, msg: "大模型服务暂时不可用..."` |
| CHAT-24 | LLM API Key 失效 | Key 无效 | `code: 5002` |
| CHAT-25 | Chroma 不可用 | Chroma 服务宕机 | 检索阶段异常，应返回 `code: 5001` |

---

### 2.2 智能对话接口 — `POST /api/chat/stream`

| 编号 | 场景 | 预期 SSE 事件流 |
|:--:|------|------|
| CHAT-S01 | 正常流式对话 | `start` → 多个 `chunk` → `done`（含 references） |
| CHAT-S02 | 参数校验失败 | 不进入 SSE，直接返回 JSON 错误 |
| CHAT-S03 | 文档未就绪 (4002) | 不进入 SSE，直接返回 JSON 错误 |
| CHAT-S04 | `start` 事件内容 | 包含 `session_id` 和 `request_id` |
| CHAT-S05 | `done` 事件内容 | 包含 `references` 数组，每项含 `chunk_id`, `content`, `score` |
| CHAT-S06 | 客户端断连 | **当前行为：对话可能不保存**（见 BUG-09） |

---

### 2.3 命中率测试接口 — `POST /api/rag/test_retrieve`

#### 参数校验

| 编号 | 场景 | 请求 | 预期结果 |
|:--:|------|------|------|
| HIT-01 | kb_id 为空 | `{"kb_id":"", "doc_id":"d1", "query":"test", "search_type":"hybrid"}` | `code: 400, msg: "缺少必填参数: kb_id"` |
| HIT-02 | doc_id 为空 | `{"kb_id":"kb1", "doc_id":"", "query":"test", "search_type":"hybrid"}` | `code: 400, msg: "缺少必填参数: doc_id"` |
| HIT-03 | query 为空 | `{"kb_id":"kb1", "doc_id":"d1", "query":"", "search_type":"hybrid"}` | `code: 400, msg: "缺少必填参数: query"` |
| HIT-04 | search_type 非法 | `search_type: "semantic"` | `code: 400, msg: "search_type 必须是 vector / keyword / hybrid"` |
| HIT-05 | search_type 为空 | `search_type: ""` | `code: 400` |
| HIT-06 | search_type=vector | 合法值 | `code: 0`，向量检索 |
| HIT-07 | search_type=keyword | 合法值 | `code: 0`，关键词检索 |
| HIT-08 | search_type=hybrid | 合法值 | `code: 0`，混合检索 |
| HIT-09 | kb_id 不存在 | 不存在的知识库 ID | `code: 404, msg: "知识库不存在"` |
| HIT-10 | doc_id 不存在 | 不存在的文档 ID | `code: 404, msg: "文档不存在或不属于该知识库"` |
| HIT-11 | 文档不属于该知识库 | doc_id 存在但 kb_id 不匹配 | `code: 404, msg: "文档不存在或不属于该知识库"` |

#### 文档状态准入 4002（V2 第十一章核心）

| 编号 | 场景 | 文档状态 | 预期结果 |
|:--:|------|------|------|
| HIT-12 | 文档 pending | status=pending | `code: 4002, msg: "文档「xxx」等待处理，请等待处理完成后再试"` |
| HIT-13 | 文档 processing | status=processing | `code: 4002, msg: "文档「xxx」正在处理中，请等待处理完成后再试"` |
| HIT-14 | 文档 failed | status=failed | `code: 4002, msg: "文档「xxx」处理失败，请等待处理完成后再试"` |
| HIT-15 | 文档 completed | status=completed | `code: 0`，正常检索 |
| HIT-16 | 4002 响应 data 字段 | 任意非 completed | `data: {"doc_id": "...", "status": "pending/processing/failed"}` |

#### 检索结果

| 编号 | 场景 | 预期结果 |
|:--:|------|------|
| HIT-17 | 检索命中 | `code: 0, total_hits > 0, hits` 数组非空 |
| HIT-18 | 检索无命中 | `code: 0, total_hits: 0, hits: []` |
| HIT-19 | 三种检索结果差异 | 同一 query，vector/keyword/hybrid 返回结果排序不同 |
| HIT-20 | hits 字段完整性 | 每项含 `chunk_id`, `content`, `score`, `source_doc`, `doc_id` |
| HIT-21 | top_n 控制 | `top_n: 3`，返回最多 3 条 |

#### 异常

| 编号 | 场景 | 预期结果 |
|:--:|------|------|
| HIT-22 | Chroma 不可用 | `code: 5001, msg: "向量库服务异常: ..."` |
| HIT-23 | 文档无分片 | `code: 0, total_hits: 0, hits: []` |

---

### 2.4 V2 权限越权专项

> ⚠️ **当前阻塞**：两个接口都没有 `user=Depends(get_current_user)` 依赖，权限校验全部无法进行。需要后端 A 和后端 B 联调加上鉴权依赖后才能执行以下用例。

| 编号 | 场景 | 预期结果 | 对应方案章节 |
|:--:|------|------|:--:|
| PERM-01 | 用户 A（组 G1 授权 KB1）对 KB2 调用 `/chat/send` | `code: 403` | 七.7.4 |
| PERM-02 | 用户 A 对 KB2 调用 `/test_retrieve` | `code: 403` | 七.7.4 |
| PERM-03 | 未分配用户组的用户调用 `/chat/send` | `code: 4001` | 七.7.2 |
| PERM-04 | 未分配用户组用户调用 `/test_retrieve` | `code: 4001` | 七.7.2 |
| PERM-05 | admin 用户访问任意 KB | `code: 0`（超管放行） | 七.7.3 |
| PERM-06 | 未登录调用 `/chat/send` | `code: 401` | 六.6.2 |
| PERM-07 | 未登录调用 `/test_retrieve` | `code: 401` | 六.6.2 |

---

### 2.5 V2 可观测性验证（Langfuse + Prometheus）

> ⚠️ **当前阻塞**：`config.py` 缺少 Langfuse/Prometheus 配置项（见 BUG-03），以下用例待配置补齐后执行。

| 编号 | 场景 | 预期结果 | 对应方案章节 |
|:--:|------|------|:--:|
| OBS-01 | 访问 `/metrics` 端点 | 返回 Prometheus 格式指标 | 八.8.3 |
| OBS-02 | 发起命中测试后检查 `/metrics` | `rag_retrieve_total` 增加 | 八.8.3.2 |
| OBS-03 | 发起对话后检查 `/metrics` | `llm_call_total` 增加 | 八.8.3.2 |
| OBS-04 | 对话接口返回 `request_id` | 响应中包含 `request_id` 字段 | 八.8.6 |
| OBS-05 | 流式接口 `start` 事件包含 `request_id` | SSE start 事件中有 `request_id` | 八.8.6 |
| OBS-06 | Langfuse Dashboard 查看对话 Trace | 可见完整链路（query → retrieval → answer → usage） | 八.8.4 |

---

## 三、Bug 汇总清单

| 级别 | 编号 | 描述 | 位置 | 状态 |
|:--:|:--:|------|------|:--:|
| 🔴 P0 | BUG-01 | **两个接口都缺少鉴权依赖**（无 `get_current_user`，无 `require_kb_access`） | `chat.py`, `rag.py` | 待修复 |
| 🔴 P0 | BUG-02 | **`init_db.py` 缺少 V2 四张表**（user_groups, user_group_members, kb_group_access, system_config） | `init_db.py` | 待修复 |
| 🔴 P0 | BUG-03 | **`config.py` 缺少 Langfuse + Prometheus 配置项** | `config.py` | 待修复 |
| 🟡 P1 | BUG-04 | `/chat/send` 响应缺少契约要求的 `query` 字段 | `chat.py` | 待修复 |
| 🟡 P1 | BUG-05 | LLM 异常检测依赖字符串前缀匹配，应用异常机制替代 | `chat.py` | 待修复 |
| 🟡 P1 | BUG-06 | `/chat/send` 和 `/chat/stream` 缺少 `search_type` 校验 | `chat.py` | 待修复 |
| 🟡 P1 | BUG-07 | `init_db.py` 缺少 V2 种子数据（admin 用户组 + 品牌配置默认值） | `init_db.py` | 待修复 |
| 🟢 P2 | BUG-08 | 两个接口都缺少 `top_n` 边界校验 | `chat.py`, `rag.py` | 待修复 |
| 🟢 P2 | BUG-09 | 流式接口客户端断连时对话记录可能丢失 | `chat.py` | 待修复 |

---

## 四、当前可测范围与阻塞项

### 当前可直接测试

- ✅ 参数校验（400 错误码）
- ✅ 知识库/文档不存在（404 错误码）
- ✅ 文档状态准入（4002 错误码）— 需数据库中有对应状态的文档
- ✅ 正常检索/对话流程（code: 0）
- ✅ 检索无命中（空结果）
- ✅ 三种检索模式切换（vector / keyword / hybrid）
- ✅ 多轮对话（session_id 传递）
- ✅ 流式 SSE 事件（start / chunk / done）

### 阻塞项（待后端修复后测试）

- ❌ 权限越权专项（403 / 4001）— 依赖 BUG-01 修复（鉴权中间件）
- ❌ Langfuse Trace 验证 — 依赖 BUG-03 修复（Langfuse 配置）
- ❌ Prometheus 指标验证 — 依赖 BUG-03 修复（Prometheus 配置）
- ❌ 用户组管理接口联调 — 依赖 BUG-02 修复（V2 表建表）

---

## 五、建议修复顺序

1. **后端 B** 补齐 `init_db.py` 中 V2 四张表 + 种子数据 → 解除 BUG-02、BUG-07
2. **后端 B** 补齐 `config.py` 中 Langfuse/Prometheus 配置 → 解除 BUG-03
3. **后端 A** 在两个接口中加上 `user=Depends(get_current_user)` 和 `require_kb_access(req.kb_id)` 依赖 → 解除 BUG-01
4. **后端 A** 修复 BUG-04（响应加 `query` 字段）、BUG-05（异常机制）、BUG-06（search_type 校验）
5. 以上完成后，测试工程师可执行完整的 V2 全量测试用例

---

*报告生成日期：2026-07-16*
*对应方案版本：V2 终稿*