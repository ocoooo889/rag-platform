# 测试报告：shanghuanhuan-rag-engine（work-shang）

| 项 | 内容 |
|---|---|
| 工作树 | `workspace_rag/work-shang` |
| 分支 / HEAD | `feature/shanghuanhuan-rag-engine` @ `7c85e9b` |
| 对比基线 | `origin/dev`（远端最新） |
| 测试时间 | 2026-07-17 |
| 本地实测端口 | API `8011`；DB `dev_shang_test_rag.db`；Collection `rag_chunks__shang_test` |
| 结论 | **后端 A（rag/chat）可启动、契约校验正常；B 路由仍为空；无鉴权；缺一键启动脚本。与前端 luoyue 字段契约存在明显不兼容风险。** |

---

## 1. 依赖 / 环境 / 启动脚本

### 1.1 通过项

- `backend/requirements.txt` 与 `dev` 一致，可安装：FastAPI / uvicorn / chromadb / openai / langfuse 等。
- `.env.example` 支持 `ENV` / `LOCAL_DB_NAME` / `CHROMA_COLLECTION_SUFFIX` / `UPLOAD_DIR` 隔离。
- `scripts/init_db.py` 可创建 7 张表并写入 admin 种子，实测成功。
- 启动方式明确（`backend` 目录）：

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

### 1.2 问题清单

#### [SHANG-D01] 无 README / 无一键 start 脚本（中）

- **现象**：工作树根无 README；`scripts/` 仅有 `init_db.py` / `self_test_rag.py` / `smoke_ab_merge.py` / `start_langfuse.sh`，无 Windows 可用的 `start_all`。
- **影响**：新人无法一键起 Chroma + API +（可选）前端。
- **建议**：补 `scripts/start_backend.ps1`（含端口/ENV 参数）与最小 README。

#### [SHANG-D02] requirements 未声明运行时可选依赖冲突面（低）

- **现象**：本分支不依赖 prometheus/loguru，但与 yulin 共用同一 conda 环境时易产生「环境有、requirements 无」的漂移。
- **建议**：并行测试强制每人独立 venv（见全局操作步骤）。

---

## 2. 接口功能测试（实测 OpenAPI）

注册路由仅 **5** 条：

| 方法 | 路径 | 结果 |
|---|---|---|
| GET | `/health` | ✅ 200，`env=dev-shang-test`，collection 后缀生效 |
| GET | `/api/health` | ✅ 200 |
| POST | `/api/rag/test_retrieve` | ✅ 缺 kb 返回业务码 404；缺字段 422 |
| POST | `/api/chat/send` | ⚠ 依赖 LLM Key，易超时/5002（未做长耗时阻塞测） |
| POST | `/api/chat/stream` | 同上 |

### 2.1 通过的契约校验

错误字段请求：

```json
{"question":"测试","mode":"keyword"}
```

返回 **422**，明确要求 `kb_id` / `doc_id` / `query` / `search_type` —— 说明后端契约稳定为：

```6:9:work-shang/backend/app/schema/rag.py
    kb_id: str
    doc_id: str
    search_type: str
    query: str
```

合法结构但 kb 不存在：

```json
{"kb_id":"kb_x","doc_id":"d_x","query":"测试","search_type":"keyword","top_n":3}
```

返回 `{"code":404,"msg":"知识库不存在"}` ✅

### 2.2 问题清单

#### [SHANG-A01] rag/chat **无鉴权**（高，延续 BUG-01）

- **文件**：`backend/app/main.py`、`backend/app/api/rag.py`、`backend/app/api/chat.py`
- **片段**：

```25:26:work-shang/backend/app/main.py
app.include_router(rag.router, prefix="/api/rag")
app.include_router(chat.router, prefix="/api/chat")
```

路由层无 `Depends(get_current_user)`。
- **风险**：与后端 B 合并后权限模型冲突；本地可匿名打检索/对话。
- **建议**：与 yulin 对齐，对 A 接口增加 JWT 依赖（或网关层统一鉴权）。

#### [SHANG-A02] 后端 B CRUD 文件仍为空壳（高，合入风险）

- **文件**：`backend/app/api/auth.py` / `kb.py` / `docs.py` / `users.py` 等长度均为 **0**。
- **现象**：`main.py` 仍只挂 rag/chat，与 `origin/dev` 一致。
- **建议**：本分支职责清晰即可，但合入前须由 yulin 分支提供 B 实现，避免空文件覆盖。

#### [SHANG-A03] chat 强依赖 LLM，无 Key 时体验差（中）

- **文件**：`backend/app/api/chat.py`、`backend/app/utils/llm_client.py`
- **建议**：自测脚本对无 Key 场景断言业务码（如 5002），避免客户端挂死；本报告未阻塞长超时。

---

## 3. 与 `origin/dev` 差异对比

`git diff --stat origin/dev...HEAD` 主要变更：

| 区域 | 说明 |
|---|---|
| `backend/app/api/chat.py` | +75/-40，对话链路/契约增强 |
| `backend/app/db/schema_compat.py` 等 | 小幅兼容 |
| `backend/app/utils/llm_client.py` | LLM 调用调整 |
| `docs/`、`frontend/tests/`、`scripts/smoke_ab_merge.py` | 测试文档与脚本（非主链路） |

### 冲突 / 兼容判断

| 点 | 判断 |
|---|---|
| 相对 dev 的 A 能力 | **向前增强**，无明显破坏 `health` / `test_retrieve` 路径 |
| 与 luoyue 前端 | **字段不兼容**（见全局风险：`doc_id` vs `doc_ids`，`search_type` vs `mode`，`hits` vs `items`） |
| 与 yulin 合入 | yulin 会大幅改 `main.py`；shang 若只改 chat，冲突可解，但需保留双端路由 |
| 空 B 文件 | 若 git merge 以空文件为准会 **抹掉** yulin 实现 —— **高风险** |

---

## 4. 风险点（本分支）

| ID | 风险 | 级别 |
|---|---|---|
| R1 | 默认 API 端口 8001、Chroma 8000 与他人冲突 | 高（并行时） |
| R2 | 默认 `LOCAL_DB_NAME` / collection 未改会覆盖同机数据 | 高 |
| R3 | A 无鉴权 | 高 |
| R4 | 空 B api 文件合入覆盖 | 高 |
| R5 | 无 Key / 无 Chroma 时 chat/vector 降级或不稳定 | 中 |

---

## 5. 本分支建议验收标准（最小）

1. `init_db` + `uvicorn :8011` + `/health` 200  
2. `POST /api/rag/test_retrieve` 缺参 422、缺库 404、completed 文档可检索  
3. ENV 隔离后 collection 名含个人后缀  
4. **不**将空 `auth.py`/`kb.py` 合入覆盖 yulin  

---

*报告人：测试工程师（本地并行测试）*
