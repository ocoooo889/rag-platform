# 最新 dev 后端测试报告（Day2 / #16+#17+#18）

| 项 | 内容 |
|---|---|
| 测试对象 | `rag-platform` 分支 `dev` @ **`4dae5ce`**（`day2-yulin #17`） |
| 前置提交 | `44e37ac` Feature/shanghuanhuan-rag-engine (#18)；`74e2600` Feature/yulin-backend (#16) |
| 测试时间 | 2026-07-17 |
| 测试角色 | 资深测试工程师 |
| 约束 | **不修改任何业务代码**；仅静态分析 + 导入验证 + 对照旧进程冒烟 |
| 总评 | **阻塞发布 / 阻塞联调。最新代码 `from app.main import app` 失败；合入残留导致语法错误与路由逻辑失效。** |

---

## 1. 结论摘要（先看这里）

| 级别 | 结论 |
|---|---|
| **P0 阻断** | `backend/app/api/auth.py` **IndentationError** → 应用无法加载、无法用最新代码启动 uvicorn |
| **P0 阻断** | `#17` 与 `#18` 合并残留：`rag.py` / `chat.py` 中 **装饰器挂在残缺函数上**，完整实现函数**未注册** |
| **P0 阻断** | `main.py` **同时**「无重复 prefix 挂载」+「带重复 prefix 挂载」→ 双路径并存，契约混乱 |
| **P0 阻断** | `scripts/init_db.py` 与 ORM（`hashed_password` / `启用` / `system_config` 等）仍不一致 → 即便能启动，登录/仪表盘/品牌易 500 |
| **P1** | `dashboard.py` 两次赋值 `APIRouter`，prefix 声明被覆盖 |
| **通过项** | `requirements.txt` 已补 `prometheus-fastapi-instrumentator`、`loguru`；B 模块文件非空；`schema_compat` 仍在 |

**门禁建议：最新 `dev` 后端不可作为今日联调/演示基线，需开发修复后回归。**

---

## 2. 变更范围盘点（相对合入前脚手架）

### 2.1 提交与意图

| 提交 | PR | 后端意图（据 commit message） |
|---|---|---|
| `74e2600` | #16 yulin-backend | 注册 B 全路由、Instrumentator、日志中间件、startup init_db |
| `44e37ac` | #18 shanghuanhuan | rag/chat 鉴权+KB 权限；契约 query/search_type；LLM→5002；schema_compat |
| `4dae5ce` | #17 day2-yulin | 声称修复双 prefix、补 requirements、JSON 登录、schema ConfigDict、与 A 合并 |

### 2.2 触及文件（HEAD 相对 #16 前关键业务点）

- `backend/app/main.py` — 路由挂载 / 监控 / startup
- `backend/app/api/auth.py` / `users.py` / `roles.py` / `kb.py` / `docs.py` / `models.py` / `user_groups.py` / `branding.py` / `dashboard.py`
- `backend/app/api/rag.py` / `chat.py` — A 能力 + 鉴权合入
- `backend/app/schema/*`、`backend/requirements.txt`
- （#18 相关）`schema_compat.py` / sqlite_helper 调用链

---

## 3. 静态质量门禁（最新代码树）

### 3.1 语法 / 导入

| 检查项 | 结果 | 证据 |
|---|---|---|
| 全量 `backend/app/**/*.py` AST | **FAIL** | 仅 `auth.py` 语法失败 |
| `from app.main import app` | **FAIL** | `IndentationError: expected an indented block after 'if' statement on line 30 (auth.py, line 32)` |

#### [BUG-DEV-01] `login_json` 函数体残缺（P0）

- **文件**：`backend/app/api/auth.py`
- **片段**：

```26:36:backend/app/api/auth.py
@router.post("/login/json", response_model=ResponseModel)
def login_json(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录接口，支持 JSON 格式，验证用户名密码并生成 JWT"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):

@router.post("/login", response_model=ResponseModel)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录接口，验证用户名密码并生成 JWT 访问令牌"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):

        return ResponseModel(code=401, msg="用户名或密码错误")
```

- **影响**：任意进程若加载最新代码即崩溃；热重载若扫到该文件也会把正在跑的服务打挂。
- **建议（给开发，测试不改代码）**：补全 `login_json` 的 `if` 分支与成功返回；删除重复的第二个 `@router.post("/login")`（`login` / `login_form` 冲突）。

### 3.2 路由处理函数注册错误（AST 确认）

| 文件 | 装饰器挂载函数 | 同名完整实现 | 实际生效行为（若能 import） |
|---|---|---|---|
| `rag.py` | `test_retrieve` L33（1 句：`require_kb_access`） | L36 无装饰器（完整检索） | **只鉴权，不检索，返回 None** |
| `chat.py` | `chat_send` L94（1 句） | L97 无装饰器 | **同上** |
| `chat.py` | `chat_stream` L164（1 句） | L167 无装饰器 | **同上** |

#### [BUG-DEV-02] A/B 合入时「半截函数」抢注册（P0）

- **文件**：`backend/app/api/rag.py`、`backend/app/api/chat.py`
- **片段（rag）**：

```31:40:backend/app/api/rag.py
@router.post("/test_retrieve")

async def test_retrieve(req: HitTestRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    await require_kb_access(req.kb_id, user, db)

async def test_retrieve(
    req: HitTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
```

- **建议**：每个路径只保留一个带 `@router` 的完整函数；删除残缺 stub。

### 3.3 `main.py` 双挂载残留

#### [BUG-DEV-03] 正确挂载与错误挂载并存（P0）

- **文件**：`backend/app/main.py`
- **现象**：先 `include_router(auth.router)`（正确，因 router 自带 `/api/auth`），再 `include_router(auth.router, prefix="/api/auth")`（再次叠加 → `/api/auth/api/auth/...`）。
- **片段**：

```55:76:backend/app/main.py
app.include_router(rag.router, prefix="/api/rag")
app.include_router(chat.router, prefix="/api/chat")

app.include_router(auth.router)
...
app.include_router(dashboard.router)

app.include_router(auth.router, prefix="/api/auth")
...
app.include_router(dashboard.router, prefix="/api/dashboard")
```

- **建议**：删除第 68–76 行带重复 prefix 的整段；仅保留无重复 prefix 的挂载（并对 `docs`/`branding`/`dashboard` 再核对一次最终 OpenAPI 路径）。

### 3.4 dashboard router 赋值覆盖

#### [BUG-DEV-04] prefix 被第二次 `APIRouter()` 冲掉（P1）

```7:9:backend/app/api/dashboard.py
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

router = APIRouter()
```

- **建议**：只保留一种定义方式，与 `main` 挂载策略一致。

---

## 4. 运行态测试说明

### 4.1 最新代码：无法启动

尝试导入失败（见 §3.1）。**因此本节无法对 `4dae5ce` 进程做真实 HTTP 绿通测试。**

### 4.2 对照：本机仍存活的旧 uvicorn（拉取前 #16 进程，端口 8001）

该进程 **OpenAPI 仍全是双 prefix**，代表 **#17 修复未进入该进程**：

| 用例 | 路径 | 结果 |
|---|---|---|
| 健康检查 | `GET /health` | ✅ 200 |
| 标准登录 | `POST /api/auth/login` | ❌ 404 |
| JSON 登录 | `POST /api/auth/login/json` | ❌ 404 |
| 知识库列表 | `GET /api/knowledge-bases` | ❌ 404 |
| 品牌 | `GET /api/system/branding` | ❌ 404 |
| 仪表盘 | `GET /api/dashboard/stats` | ❌ **500**（schema：`documents.created_at` 等历史问题） |
| OpenAPI | — | 仅见 `/api/auth/api/auth/login` 等双前缀路径 |

> 说明：旧进程超时项（rag/metrics）可能与进程卡顿/重载有关，不作为最新代码通过依据。

### 4.3 计划中的功能测试矩阵（修复后回归用）

| 模块 | 用例 | 预期 | 当前最新代码 |
|---|---|---|---|
| 启动 | `uvicorn app.main:app` | 启动成功 | ❌ 语法错误 |
| Auth | form `/api/auth/login` | 200 + token | ❌ 无法测 / 文件残缺 |
| Auth | JSON `/api/auth/login/json` | 200 + token | ❌ 函数未写完 |
| Auth | 错密 | 业务码 401 | 未测 |
| Dashboard | `/api/dashboard/stats` | code=0 | 旧进程 500；新代码未起 |
| KB/Docs/Users/Roles/Models/Groups | CRUD + 401 未登录 | 契约路径 200/401 | 路径双挂风险 |
| Branding | GET 免登 | 200/4003 | 缺表风险 |
| RAG | 未登录 | **401**（#18） | 残缺 handler 风险 |
| RAG | 已登录 + 缺参 | 422/业务 400 | 未测 |
| Chat | 非法 search_type | 400 | 未测 |
| Chat | LLM 失败 | 业务码 5002 | 未测 |
| Metrics | `/metrics` | 200 | requirements 已声明依赖 ✅ |
| 依赖 | 干净 venv `pip install -r` | 可装齐 | requirements 已含 prometheus/loguru ✅ |

---

## 5. 数据层与契约风险（未因 #17 消除）

| ID | 问题 | 级别 |
|---|---|---|
| BUG-DEV-05 | `init_db`：`password_hash` + `active` + 角色名「管理员」；ORM：`hashed_password` + `启用`；`is_admin` 比 `"admin"` | P0 |
| BUG-DEV-06 | ORM 有 `system_config` / `user_groups`，`init_db` 未建；无统一 `create_all` | P0 |
| BUG-DEV-07 | documents：`uploaded_at` vs ORM `created_at` → dashboard count 易 500 | P0 |
| BUG-DEV-08 | KnowledgeBaseOut 等处 `id` 类型（int/str）与库 TEXT id 潜在不一致 | P1 |
| INFO | `schema_compat.ensure_rag_schema` 仅补 chunks/conversations，**不解** users 列名冲突 | — |

---

## 6. 合入质量评价（测试视角）

| 维度 | 评价 |
|---|---|
| #16 功能增量 | B 模块代码体量到位，但双 prefix + schema 未闭环 |
| #18 意图 | 鉴权/契约修复方向正确，但与 #17 合并后出现**半截函数** |
| #17 意图 | 声称修双 prefix / 补依赖：requirements **做到**；双 prefix **未删干净**；auth JSON 登录 **合坏** |
| 可测试性 | 最新树 **不可启动** → 自动化/手工接口测试均无法在 HEAD 上执行 |
| 回归风险 | 热重载一旦加载新 `auth.py`，会直接打挂旧服务 |

---

## 7. 给开发的修复优先级（测试验收点）

1. **修 `auth.py` 语法**，保证 `python -c "from app.main import app"` 通过  
2. **合并 `rag.py`/`chat.py` 为单函数注册**，OpenAPI 行为 = 鉴权 + 原业务  
3. **`main.py` 去掉重复 prefix 挂载段**，OpenAPI **不得**再出现 `/api/xxx/api/xxx`  
4. **统一 DB schema**（init_db 或 ORM+create_all 二选一），登录/dashboard/branding 冒烟过  
5. 重启干净进程后按 §4.3 矩阵回归，输出第二轮「可联调」报告  

---

## 8. 测试环境记录

| 项 | 值 |
|---|---|
| 仓库路径 | `workspace_rag/rag-platform` |
| `git rev-parse HEAD` | `4dae5ce` |
| Python | Anaconda `gpttest` |
| 静态脚本 | `_tmp_dev_backend_test.py`（一次性探测，非产品代码） |
| 代码修改 | **无** |

---

*报告人：测试工程师 · 仅测试与文档产出*
