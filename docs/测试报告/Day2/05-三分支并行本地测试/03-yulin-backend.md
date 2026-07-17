# 测试报告：yulin-backend（work-yulin）

| 项 | 内容 |
|---|---|
| 工作树 | `workspace_rag/work-yulin` |
| 分支 / HEAD | `feature/yulin-backend` @ `a0f743d` |
| 对比基线 | `origin/dev`（`main` 仅 rag/chat） |
| 测试时间 | 2026-07-17 |
| 本地实测端口 | API `8013`；DB `dev_yulin_test_rag.db`；Collection `rag_chunks__yulin_test` |
| 结论 | **B 模块代码体量大且已挂入 main，但存在「双 prefix 路由」+「ORM 与 init_db 表结构不一致」双重阻断；登录/仪表盘/品牌配置实测 500；标准路径 404。当前不可作为可联调后端。** |

---

## 1. 依赖 / 环境 / 启动脚本

### 1.1 通过项

- 进程可启动：`uvicorn app.main:app --port 8013`
- startup 会跑 `scripts/init_db.py`（种子写入成功日志可见）
- `/health` ✅；`/metrics` ✅（Prometheus Instrumentator 生效）
- A 侧 `POST /api/rag/test_retrieve` 仍可按契约返回业务码（缺库 404）

### 1.2 问题清单

#### [YULIN-D01] `requirements.txt` 未声明已使用的依赖（中）

- **文件**：`backend/requirements.txt`（与 dev 相同，无 prometheus/loguru）
- **代码**：

```15:15:work-yulin/backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator
```

```python
# backend/app/utils/logger.py
from loguru import logger
```

- **现象**：干净 venv 按 requirements 安装后 **无法启动**；当前测试机因全局环境已装而侥幸通过。
- **修复建议**：requirements 增加：
  - `prometheus-fastapi-instrumentator`
  - `loguru`

#### [YULIN-D02] 启动时强制 `subprocess` 跑 init_db（中）

- **片段**：

```68:74:work-yulin/backend/app/main.py
@app.on_event("startup")
async def startup():
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "init_db.py"
    if script_path.exists():
        subprocess.run([sys.executable, str(script_path)], check=True)
```

- **风险**：每次启动重跑种子；`INSERT OR IGNORE` 虽较安全，但与 ORM 期望 schema 冲突后「表已存在但列错」无法自愈。
- **建议**：启动改为 `Base.metadata.create_all` + 独立 seed；或统一一份 schema 源。

---

## 2. 接口功能测试（OpenAPI 实测）

OpenAPI 暴露 **24** 条路径，但大量为 **双 prefix**：

| 期望契约路径 | 实际注册路径 | 实测 |
|---|---|---|
| `POST /api/auth/login` | `POST /api/auth/api/auth/login` | 期望路径 **404**；实际路径 **500** |
| `GET /api/knowledge-bases` | `GET /api/knowledge-bases/api/knowledge-bases` | 期望 **404**；实际 **401**（路由存在） |
| `GET /api/users` | `GET /api/users/api/users` | 同上 **401** |
| `GET /api/dashboard/stats` | 同路径（dashboard 无双挂） | **500** |
| `GET /api/system/.../branding` | `GET /api/system/branding/api/system/branding` | **500** |
| 文档 | `/api/docs/api/knowledge-bases/{kb_id}/documents` | **401**（双 prefix） |
| `/metrics` | `/metrics` | ✅ 200 |
| `/api/rag/test_retrieve` | 正常（rag router 无自带 prefix） | ✅ 业务 404 |

### 2.1 问题清单

#### [YULIN-A01] **Router 双 prefix**（阻断，P0）

- **文件**：`backend/app/main.py` + 各 `api/*.py`
- **根因**：子路由已带 `prefix="/api/..."`，`main` 又再次 `include_router(..., prefix="/api/...")`。
- **片段**：

```55:65:work-yulin/backend/app/main.py
app.include_router(rag.router, prefix="/api/rag")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(users.router, prefix="/api/users")
app.include_router(roles.router, prefix="/api/roles")
app.include_router(kb.router, prefix="/api/knowledge-bases")
app.include_router(docs.router, prefix="/api/docs")
app.include_router(models.router, prefix="/api/models")
app.include_router(user_groups.router, prefix="/api/user-groups")
app.include_router(branding.router, prefix="/api/system/branding")
app.include_router(dashboard.router, prefix="/api/dashboard")
```

```17:17:work-yulin/backend/app/api/auth.py
router = APIRouter(prefix="/api/auth", tags=["auth"])
```

```12:12:work-yulin/backend/app/api/kb.py
router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])
```

```17:17:work-yulin/backend/app/api/docs.py
router = APIRouter(prefix="/api", tags=["documents"])
```

- **修复建议（推荐）**：`main` 中对 B 路由改为 `app.include_router(auth.router)`（去掉重复 prefix）；或删掉子路由上的 `prefix`，只在 main 挂一次。  
- **验收**：OpenAPI 路径恢复为 `/api/auth/login`、`/api/knowledge-bases`、`/api/knowledge-bases/{id}/documents/upload` 等契约路径。

#### [YULIN-A02] ORM 模型与 `init_db.py` schema **严重不一致**（阻断，P0）

- **文件**：`backend/app/db/models.py` vs `scripts/init_db.py`
- **实测错误**：
  - 登录：`sqlite3.OperationalError: no such column: users.hashed_password`（表字段为 `password_hash`）
  - Dashboard：`no such column: documents.created_at`（init 为 `uploaded_at`）
  - Branding：`no such table: system_config`
  - 且 ORM 期望 `user_groups` / `kb_group_access` 等，init_db **未建**

| 维度 | init_db | ORM (models.py) |
|---|---|---|
| users.id | TEXT (`u001`) | Integer PK |
| 密码列 | `password_hash` | `hashed_password` |
| status | `active` | `启用` |
| roles.name | `管理员` | `is_admin` 判断 `"admin"` |
| documents 时间列 | `uploaded_at` | `created_at` |
| system_config / user_groups | 无 | 有 |

- **片段（种子）**：

```132:133:work-yulin/scripts/init_db.py
    INSERT OR IGNORE INTO users (id, username, password_hash, display_name, role_id, status, created_at)
    VALUES ('u001', 'admin', '$2b$12$LJ3m4ys3GZfnYMz8kVsKaOCG4.5Qh8rYFJR6vJb5JNqLmR9f7Xh3e', '管理员', 'r001', 'active', datetime('now'));
```

```14:21:work-yulin/backend/app/db/models.py
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    ...
    status = Column(String, default="启用") # 启用 / 已停用
```

```8:14:work-yulin/backend/app/utils/permission.py
def is_admin(user: User) -> bool:
    ...
    return role_name == "admin"
```

- **修复建议**：选定单一真相源——
  1. 以 ORM 为准：重写 `init_db` / migration，种子角色名 `admin`，status `启用`，列名对齐，并 `create_all` 补齐 `system_config`、用户组表；或  
  2. 以 init_db 为准：改 ORM 列名与类型，并改 `is_admin` 判断中文「管理员」。
- **另**：仓库中 **无** `Base.metadata.create_all`，仅靠 init_db，新表永远不会出现。

#### [YULIN-A03] 登录使用 `OAuth2PasswordRequestForm`（中）

- **文件**：`backend/app/api/auth.py`
- **现象**：必须 `application/x-www-form-urlencoded`（`username`/`password`），JSON body 不兼容。
- **建议**：与前端约定 form；或同时提供 JSON Login DTO。

#### [YULIN-A04] A 接口仍无鉴权（中，与 shang 同类）

- rag/chat 在本分支仍可匿名调用（OpenAPI 可见且实测可访问）。

#### [YULIN-A05] Pydantic `orm_mode` / `model_*` 命名告警（低）

- 启动日志大量 UserWarning；建议迁 `from_attributes`、关闭 protected namespace 警告。

---

## 3. 与 `origin/dev` 差异对比

`24 files, +1730/-49`，核心：

- 新增完整 B API：auth/users/roles/kb/docs/models/user_groups/branding/dashboard
- 新增 ORM、schema、auth/permission/logger/metrics
- **改写** `main.py`：挂载全部路由 + Instrumentator + startup init_db
- 同步带上 chat/schema_compat/llm 等小改（与 shang 部分重叠，合入易冲突）

### 冲突 / 兼容判断

| 点 | 判断 |
|---|---|
| 相对 dev | **功能面大幅前进**，但当前运行态不可用 |
| 与 shang | 双方都改 `chat.py` / `llm_client` → merge 冲突概率高，需协调 |
| 与 luoyue | 即使修双 prefix，仍需统一字段与鉴权 Header；前端 proxy 仍错端口 |
| 空文件风险 | yulin 填满了 api 文件；**切勿被 shang/luoyue 空文件回滚** |

---

## 4. 风险点（本分支）

| ID | 风险 | 级别 |
|---|---|---|
| R1 | 双 prefix 导致前端/契约全部打空 | P0 |
| R2 | ORM vs init_db 列/表不一致 → 全链路 500 | P0 |
| R3 | requirements 缺 prometheus/loguru | 高 |
| R4 | 与 shang 改动重叠文件 merge | 高 |
| R5 | startup 反复 init_db + 错 schema 固化 | 高 |
| R6 | 默认端口 8001 / Chroma 8000 并行冲突 | 中 |

---

## 5. 本分支建议验收标准（最小）

1. OpenAPI **无** `/api/auth/api/auth/login` 这类双前缀  
2. `POST /api/auth/login` form 登录返回 token（非 500）  
3. `GET /api/dashboard/stats`、`GET /api/system/branding` 200/业务码  
4. 干净 venv：`pip install -r requirements.txt` 后可启动  
5. 与前端约定路径一致后，KB CRUD 冒烟通过  

---

*报告人：测试工程师（本地并行测试）*
