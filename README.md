# 智能 RAG 平台

基于检索增强生成（RAG）技术的企业级知识问答系统。

> **重要**：GitHub 默认分支 `main` 可能不是最新可运行代码。请先切到 **`dev`**（或团队指定的功能分支），再按下方最短路径启动。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus（Node **≥ 18**） |
| 后端 | FastAPI（Python **3.10–3.12**，推荐 3.11） |
| 数据库 | SQLite |
| 向量库 | Chroma（HTTP，端口 **8000**） |
| 重排 | Rerank 微服务（端口 **8002**） |
| LLM / Embedding | OpenAI 兼容接口（可填百炼等） |

## 最短正确路径（真实后端 · 推荐）

开发默认走**真实后端**（`VITE_USE_MOCK=false`），前端 Vite 将 `/api` 代理到 **8001**。

```bash
git clone https://github.com/ocoooo889/rag-platform.git
cd rag-platform
git checkout dev   # 或你的可运行分支，勿停在空/旧 main

cp .env.example .env
# 必改：ENV / LOCAL_DB_NAME / CHROMA_COLLECTION_SUFFIX / UPLOAD_DIR / OPENAI_API_KEY
# CHROMA_HOST 须为 127.0.0.1（与 chroma --host 127.0.0.1 一致，避免 Windows 只绑 ::1）

cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# 终端 1 — 必须先有 Chroma（固定绑 IPv4，勿省略 --host）
chroma run --path ../chroma_data --host 127.0.0.1 --port 8000

# 终端 2 — 主 API
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 终端 3 — Rerank（对话/命中测试开启重排时需要）
uvicorn rerank_service.main:app --host 127.0.0.1 --port 8002 --reload

# 终端 4 — 前端
cd ../frontend
npm ci
npm run dev
```

| 项 | 地址 / 账号 |
|----|-------------|
| 前端 | http://127.0.0.1:5173 |
| API 文档 | http://127.0.0.1:8001/docs |
| 后端健康 | http://127.0.0.1:8001/health |
| Rerank | http://127.0.0.1:8002/health |
| Chroma 自检 | http://127.0.0.1:8000/api/v2/heartbeat （勿用已废弃的 `/api/v1/`） |
| 默认管理员 | `admin` / `admin123` |

**一键启动**（首次 / 装依赖，含 Chroma + 后端 + Rerank + 前端）：

```bash
# Windows
scripts\start_all.bat

# macOS / Linux
bash scripts/start_all.sh
```

**快速重启**（已装好依赖，几秒级，推荐日常用）：

```bash
# Windows
scripts\restart_dev.bat

# macOS / Linux
bash scripts/restart_dev.sh
```

停止本机开发端口：`scripts\stop_all.bat` / `scripts/stop_all.sh`。

## Docker 一键部署（对外端口 8520）

```bash
cp .env.example .env   # 填入 OPENAI_API_KEY 等
docker compose up -d --build
```

浏览器打开：**http://localhost:8520**  
详细说明见 [`docs/Docker部署说明.md`](docs/Docker部署说明.md)。

---

## 端口约定（勿混用）

与团队端口明细（`../端口明细0720.md`，相对本仓库）一致：

| 端口 | 功能 | bind | 健康检查 | 日常是否必起 |
|------|------|------|----------|--------------|
| **8000** | Chroma 向量库 | `127.0.0.1` | `GET /api/v2/heartbeat` | 必起（先起） |
| **8001** | FastAPI 主 API（防注入 / 意图 / 切分 / 重写 / 混合检索 / 模型热读 / 评测） | `0.0.0.0` | `GET /health` | 必起（依赖 8000；Redis 见下） |
| **8002** | Rerank 重排微服务 | `127.0.0.1` | `GET /health` | 必起（开启重排时；桩可无模型） |
| **5173** | Vite 前端开发 | `127.0.0.1` | 页面可开 | 必起；Day1 代理 **8001** |
| **8520** | Docker SPA 入口 | 宿主机映射 | 打开首页 | 可选 |
| **6379** | Answer Redis 缓存 | `127.0.0.1` | `PING` | Day2 可选（明细中 8001 可依赖此项；本地演示常可暂不起） |
| **8003** | 网关负载 · 后端副本1 | `0.0.0.0` | `GET /health` | Day2 可选 |
| **8004** | 网关负载 · 后端副本2 | `0.0.0.0` | `GET /health` | Day2 可选 |
| **8080** | Nginx 网关（统一入口 + SSE 粘性） | `0.0.0.0` | `GET /health` → 反代后端 | Day2 可选；压测时前端代理改 **8080** |

前端 `VITE_API_PROXY`：Day1 指向 **8001**，不要指向 8000（那是 Chroma）；Day2 压测改 **8080**。  
防注入 / 意图 / 切分 / 重写 / 混合检索 / 模型配置 / 评测均跑在 **8001**（及副本）进程内，不另占端口。

---

## `.env` 与 `CHROMA_HOST`（固定用 127.0.0.1）

复制模板：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `ENV` / `LOCAL_DB_NAME` / `CHROMA_COLLECTION_SUFFIX` / `UPLOAD_DIR` | 每人隔离 |
| `OPENAI_API_KEY` | 必填真实 Key |
| `CHROMA_HOST` | **固定 `127.0.0.1`**（与下方 chroma 启动参数一致） |
| `CHROMA_PORT` | `8000` |
| `CHAT_RETRIEVE_MODE` | 建议 `balanced`（真向量；默认已是）。`fast` 会让对话跳过向量直接 BM25 |
| `ENABLE_INTENT_ROUTE` | 意图路由（闲聊/能力说明跳过检索），默认开启；`false` 可关 |

### 为什么以前会报「Chroma 未启动」

Windows 上 `chroma run` **不写 `--host`** 时，常只监听 IPv6（`[::1]:8000`）。  
后端 / 浏览器用 `127.0.0.1` 去连就会失败，于是出现「已切换关键词检索」。

**固定做法（推荐，以后都按这个）：**

```bash
chroma run --path ./chroma_data --host 127.0.0.1 --port 8000
```

`.env`：

```bash
CHROMA_HOST=127.0.0.1
CHROMA_PORT=8000
```

自检：浏览器打开 http://127.0.0.1:8000/api/v2/heartbeat 必须能通。  
日常重启用 `scripts\restart_dev.bat`（会自动带 `--host 127.0.0.1` 并等心跳后再启后端）。

---

## 账号与权限

- **全功能验收**请用管理员：`admin` / `admin123`（系统概览 Dashboard、知识库、文档等 **仅 admin**）
- 普通用户登录后默认进入智能对话，看不到 Dashboard / 知识库管理
- 可选创建演示普通用户（仓库根目录）：

```bash
# 需后端已在 8001 运行
python scripts/_seed_demo_user.py
# 账号：demo / demo123（仅智能对话等普通用户权限）
```

后端启动时会自动建表 + 种子数据；`python scripts/init_db.py` **可选**（须在**仓库根目录**执行）。

---

## 前端联调环境变量

配置文件：`frontend/.env.development`（可被 `.env.local` / `.env.development.local` 覆盖）。

| 变量 | 含义 | 推荐（真实后端） |
|------|------|------------------|
| `VITE_USE_MOCK` | `true` 走 Mock；默认 `false` | `false` |
| `VITE_API_PROXY` | Vite `/api` 代理目标 | `http://127.0.0.1:8001` |
| `VITE_API_BASE_URL` | 开发建议留空走代理 | （空） |
| `VITE_DEV_PORT` | 开发端口，默认 5173 | `5173` |
| `VITE_CHAT_SESSION_API` | 是否请求会话列表/消息/删除等 | `true` |

```bash
cd frontend
npm run typecheck   # 可选
npm run build       # 可选生产构建
npm run dev         # 开发：http://127.0.0.1:5173
```

纯前端演示可临时用 `frontend/.env.mock`（`VITE_USE_MOCK=true`），联调与验收请保持 Mock 关闭。

---

## 前后端 API（联调要点）

主链路路径已对齐，前端经 Vite 代理访问同一套后端路由。常用约定：

| 能力 | 路径 |
|------|------|
| 登录 | `POST /api/auth/login`（form：`username` / `password`） |
| 流式对话 | `POST /api/chat/stream`（需 `kb_id`；可选 `enable_rerank`） |
| 会话列表 | `GET /api/chat/sessions?kb_id=`（需开启 `VITE_CHAT_SESSION_API`） |
| 切分策略 | `GET /api/split-strategies`（与 `/api/documents/split-strategies` 等价） |
| 文档上传 | `POST /api/knowledge-bases/{kb_id}/documents/upload` |
| 索引配置 | `GET/PUT /api/knowledge-bases/{kb_id}/index-config` |
| 运行时模型 | `GET/PUT /api/runtime-config/models` |
| 命中测试 | `POST /api/rag/test_retrieve` |
| 评测任务 | `/api/eval/tasks` 等 |

说明：

- 会话**创建**由前端生成本地 `session_id`，首条 stream 时后端落库（无独立 create 接口）。
- 文档列表后端返回全量，前端本地分页。
- 完整 OpenAPI：http://127.0.0.1:8001/docs

---

## 项目结构

```
rag-platform/
├── backend/                 # FastAPI（uvicorn 工作目录一般在此）
│   ├── app/
│   ├── rerank_service/      # Rerank 微服务（8002）
│   ├── requirements.txt
│   └── venv/                # 本地虚拟环境（gitignore）
├── frontend/                # Vue 3 + Vite 前端
├── chroma_data/             # Chroma 持久化（gitignore）
├── uploads/                 # 上传文件（gitignore）
├── docs/                    # 契约、迁移说明、Day1～DayN 测试报告
├── scripts/
│   ├── start_all.bat / .sh  # 首次一键启动（含 pip / npm）
│   ├── restart_dev.bat / .sh # 日常快速重启（等 Chroma 心跳）
│   ├── stop_all.bat / .sh
│   ├── init_db.py           # 可选初始化
│   └── _seed_demo_user.py   # 可选演示用户
├── demo-materials/          # 演示文档与题集
├── .env.example             # 环境变量模板（勿提交真实 .env）
└── README.md
```

---

## 核心功能

- **RAG 智能对话**：知识库问答、SSE 流式、多轮会话、检索模式徽章
- **意图路由**：闲聊 / 能力说明跳过检索（后端规则；`ENABLE_INTENT_ROUTE`）
- **前端输入缓冲**：直白敏感词提示与发送阻断（体验层，不替代后端安全）
- **命中率测试**：向量 / 关键词 / 混合检索，支持 Rerank 与 TopN
- **知识库与文档管理**（admin）：多格式上传（md/txt/pdf/docx/html/csv）、切分策略下拉来自 `/api/split-strategies`
- **索引配置与重建**：chunk / hybrid / 默认检索模式 / enable_rerank / top_n
- **大模型运行配置**：热读 `runtime-config/models`（禁止前端硬编码模型名与区间）
- **评测任务**：创建、跑批、对比
- **用户权限**：JWT + 角色 + 用户组
- **自定义设置**：主题色 / Logo；日间 / 夜间模式（管理后台）

## 团队

| 编号 | 角色 | 职责 |
|:----:|------|------|
| 6号 | 项目负责人 | 总控 + 规范输出 + 风险把控 |
| 3号 | 后端 A | RAG 引擎 / Rerank |
| 4号 | 后端 B | CRUD 接口 / 主 API |
| 1号 | 前端 A | 管理后台 |
| 2号 | 前端 B | RAG 页面（对话 / 命中 / 文档等） |
| 5号 | 测试 | 用例与验收 |
