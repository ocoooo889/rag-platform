# 智能 RAG 平台

基于检索增强生成（RAG）技术的企业级知识问答系统。

> **重要**：GitHub 默认分支 `main` 可能不是最新可运行代码。请先切到 **`dev`**（或团队指定的功能分支，如 `zhangyu-mlbg`），再按下方最短路径启动。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Element Plus（Node **≥ 18**） |
| 后端 | FastAPI（Python **3.10–3.12**，推荐 3.11） |
| 数据库 | SQLite |
| 向量库 | Chroma（Http 服务，端口 **8000**） |
| LLM / Embedding | OpenAI 兼容接口（可填百炼等） |

## 最短正确路径（给队友）

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

# 终端 2 — 后端
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 终端 3 — 前端
cd ../frontend
npm ci
npm run dev
```

| 项 | 地址 / 账号 |
|----|-------------|
| 前端 | http://127.0.0.1:5173 |
| API 文档 | http://127.0.0.1:8001/docs |
| Chroma 自检 | http://127.0.0.1:8000/api/v2/heartbeat （勿用已废弃的 `/api/v1/`） |
| 默认管理员 | `admin` / `admin123` |

**一键启动**（首次 / 装依赖）：

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

---

## 端口约定（勿混用）

| 服务 | 端口 |
|------|------|
| Chroma 向量库 | **8000** |
| FastAPI 后端 | **8001** |
| Vite 前端 | **5173** |

前端代理必须指向 **8001**，不要指向 8000（那是 Chroma）。

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

| 变量 | 含义 | 示例 |
|------|------|------|
| `VITE_USE_MOCK` | `true` 走 Mock；development 默认 `false` | `false` |
| `VITE_API_PROXY` | Vite `/api` 代理目标（**默认 8001**） | `http://127.0.0.1:8001` |
| `VITE_API_BASE_URL` | 开发建议留空走代理 | （空） |
| `VITE_DEV_PORT` | 开发端口，默认 5173 | `5174` |
| `VITE_CHAT_SESSION_API` | 是否请求会话 CRUD；`.env.development` 已为 `true` | `true` |

```bash
cd frontend
npm run dev
```

---

## 项目结构

```
rag-platform/
├── backend/                 # FastAPI 后端（工作目录一般在此启动 uvicorn）
│   ├── app/
│   ├── requirements.txt
│   └── venv/                # 本地虚拟环境（gitignore）
├── frontend/                # Vue 3 前端
├── chroma_data/             # Chroma 持久化目录（仓库根，gitignore；脚本 --path ./chroma_data）
├── uploads/                 # 上传文件（gitignore；.env 里 UPLOAD_DIR 可再分子目录）
├── docs/                    # 契约与测试文档
├── scripts/
│   ├── start_all.bat / .sh  # 首次一键启动（含 pip）
│   ├── restart_dev.bat / .sh # 日常快速重启（等 Chroma 心跳）
│   ├── stop_all.bat / .sh
│   ├── init_db.py           # 可选初始化
│   └── _seed_demo_user.py   # 可选演示用户
├── demo-materials/          # 演示文档
├── docs/                    # 契约与测试文档（含 Day1～Day4 报告）
├── .env.example             # 环境变量模板（勿提交真实 .env）
└── README.md
```

---

## 核心功能

- **RAG 智能对话**：知识库问答，SSE 流式输出
- **命中率测试**：向量 / BM25 / 混合检索
- **知识库与文档管理**（admin）
- **用户权限**：JWT + 角色 + 用户组
- **自定义设置**：主题色 / Logo（权限按角色区分）
- **日间 / 夜间模式**（管理后台；登录页不同步）

## 团队

| 编号 | 角色 | 职责 |
|:----:|------|------|
| 6号 | 项目负责人 | 总控 + 规范输出 + 风险把控 |
| 3号 | 后端 A | RAG 引擎 |
| 4号 | 后端 B | CRUD 接口 |
| 1号 | 前端 A | 管理后台 |
| 2号 | 前端 B | RAG 页面 |
| 5号 | 测试 | 用例与验收 |
