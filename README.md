
﻿# 智能 RAG 平台

基于检索增强生成（RAG）技术的企业级知识问答系统。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Element Plus |
| 后端 | FastAPI (Python 3.11) |
| 数据库 | SQLite |
| 向量库 | Chroma (1536 维, 余弦相似度) |
| LLM | OpenAI gpt-4o-mini |
| Embedding | text-embedding-3-small (1536 维) |
| 结构化日志 | loguru (JSON 格式) |
| 指标监控 | Prometheus + prometheus-fastapi-instrumentator |
| LLM 可观测 | Langfuse (全链路 Trace) |

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd rag-platform
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少修改以下字段：
#   ENV=dev-你的姓名拼音
#   LOCAL_DB_NAME=dev_你的姓名拼音_rag.db
#   CHROMA_COLLECTION_SUFFIX=_你的姓名拼音
#   UPLOAD_DIR=./uploads/dev_你的姓名拼音
#   OPENAI_API_KEY=sk-你的Key
```

### 3. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 4. 初始化数据库

```bash
python scripts/init_db.py
```

### 5. 启动服务

**方式一：一键启动**

```bash
# Windows
scripts/start_all.bat

# macOS / Linux
bash scripts/start_all.sh
```

**方式二：分别启动**

```bash
# 终端 1: 启动 Chroma
chroma run --path ./chroma_data --port 8000

# 终端 2: 启动后端
cd backend
uvicorn app.main:app --reload --port 8001

# 终端 3: 启动前端
cd frontend
npm run dev
```

### 6. 访问

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:5173 |
| API 文档 | http://localhost:8001/docs |
| 健康检查 | http://localhost:8001/health |

默认管理员账号：`admin` / `admin123`

## 项目结构

```
rag-platform/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── api/            # 接口路由（auth/users/roles/user_groups/kb/docs/models/branding/rag/chat）
│   │   ├── db/             # 数据库模型（models.py + database.py）
│   │   ├── rag_engine/     # RAG 引擎（splitter/embedder/retriever/generator/rag_pipeline）
│   │   ├── utils/          # 工具模块（llm_client/auth/permission/logger/metrics）
│   │   ├── schema/         # Pydantic 数据模型
│   │   ├── config.py       # 全局配置（定死参数）
│   │   └── main.py         # FastAPI 应用入口
│   ├── prompts/            # LLM 提示词模板
│   ├── logs/               # 日志目录（V2 新增，gitignore）
│   ├── uploads/branding/   # 品牌 Logo 上传目录（V2 新增）
│   └── chroma_data/        # Chroma 向量数据（gitignore）
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── views/          # 页面组件（Dashboard/RoleManage/UserManage/UserGroupManage/ModelManage/BrandingConfig/KbManage/DocManage/HitTest/ChatDialog）
│   │   ├── components/     # 公共组件（AppLayout）
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # Pinia 状态管理（user/branding）
│   │   ├── api/            # 接口封装（index/rag）
│   │   ├── utils/          # 工具函数（request 拦截器）
│   │   ├── mock/           # Mock 数据（mock_data_A/B.json）
│   │   ├── App.vue         # 根组件
│   │   └── main.js         # 入口文件
│   ├── package.json        # 依赖配置（含 pinia-plugin-persistedstate）
│   ├── vite.config.js      # Vite 构建配置
│   └── index.html          # HTML 入口
├── docs/                   # 契约与管理文档
│   ├── api_contract.md     # 接口契约（V2: 11 错误码 + 用户组/品牌/logo接口）
│   ├── db_schema.md        # 数据库设计（V1 7 表 + V2 4 表 = 11 表）
│   ├── 2天项目排期表.md     # 排期计划
│   ├── 风险与预案清单.md    # 风险管理（R01-R16）
│   ├── 交付验收标准.md       # 交付标准
│   ├── 演示操作流程.md       # 演示流程
│   ├── monitoring_guide.md # V2 新增：监控配置指南
│   ├── 测试用例/            # 测试用例目录
│   └── meeting/             # 会议记录目录
├── scripts/                # 运维脚本
│   ├── init_db.py          # 数据库一键初始化（含 V2 4 表种子数据）
│   ├── start_all.sh        # 一键启动（Linux/macOS）
│   ├── start_all.bat       # 一键启动（Windows，含前端）
│   └── start_langfuse.sh   # V2 新增：Langfuse 启动脚本
├── prompts/                # LLM 提示词模板
├── demo-materials/         # 演示测试材料（3篇测试文档 + 标准问题集）
├── 契约文件2.md             # V2 增量契约（5项增量）
├── Git分支管理规范.md        # Git 工作流规范
├── .env.example            # 环境变量模板（含 V2 Langfuse/Prometheus 配置）
└── .gitignore
```

## 核心功能

- **RAG 智能对话**：基于知识库文档进行问答，支持流式 SSE 输出
- **命中率测试**：支持向量检索 / 全文检索(BM25) / 混合检索三种方式
- **知识库管理**：创建知识库、上传文档（.md / .txt）、自动切片入库
- **用户权限**：JWT 鉴权 + 三级角色 + 用户组权限隔离（V2 新增）
- **白标定制（OEM）**：购买方可更换系统名称、Logo、主题色（V2 新增）
- **可观测性**：日志管理 + Prometheus 指标 + Langfuse LLM 追踪（V2 新增）
- **文档状态管控**：文档未处理完成不可检索，自动等待提示（V2 新增）
- **环境隔离**：每人独立 SQLite + Chroma 集合 + 上传目录，互不干扰

## 团队

| 编号 | 角色 | 职责 |
|:----:|------|------|
| 6号 | 项目负责人 | 总控 + 规范输出 + 风险把控 |
| 3号 | 后端 A | RAG 引擎（检索/向量化/对话） |
| 4号 | 后端 B | CRUD 接口（用户/角色/知识库/文档） |
| 1号 | 前端 A | 管理后台（角色/用户/模型管理） |
| 2号 | 前端 B | RAG 页面（知识库/文档/命中测试/智能对话） |
| 5号 | 测试 | 测试用例 + 回归测试 + 质量验收 |

# rag-platform
智能RAG管理后台项目，包含前端管理页面、RAG检索引擎、知识库评测模块，由6人团队协作开发
