# Docker 部署说明（端口 8520）

对外访问地址：**http://localhost:8520**

## 架构

```
浏览器 → :8520 (nginx/frontend)
              ├─ /          → 前端静态页
              └─ /api/*     → backend:8001
                                └─ chroma:8000（内网）
```

宿主机只暴露 **8520**；Chroma / 后端不映射到宿主机，避免和本地开发端口冲突。

Chroma 使用本仓库 `docker/chroma/Dockerfile` 安装与后端一致的 `chromadb==1.5.9`，不依赖 Docker Hub 上的 `chromadb/chroma` 镜像 tag。

## 前置条件

- 已安装 [Docker](https://docs.docker.com/get-docker/) 与 Docker Compose v2
- 项目根目录有 `.env`（可从 `.env.example` 复制）并填好：
  - `OPENAI_API_KEY`（或兼容接口 Key）
  - `OPENAI_BASE_URL` / `LLM_MODEL` / `EMBEDDING_MODEL`（按你的供应商）

Compose 会自动覆盖：

| 变量 | Docker 内取值 |
|------|----------------|
| `CHROMA_HOST` | `chroma`（服务名） |
| `CHROMA_PORT` | `8000` |
| `LOCAL_DB_NAME` | `/data/db/rag.db` |
| `UPLOAD_DIR` | `/data/uploads` |
| `DOTENV_OVERRIDE` | `false`（compose 环境优先） |

## 启动

```bash
# 项目根目录
cp .env.example .env   # 若还没有
# 编辑 .env 填入真实 API Key

docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f backend
```

打开：http://localhost:8520  
默认管理员：`admin` / `admin123`

健康检查：http://localhost:8520/health

## 停止 / 清理

```bash
docker compose down          # 停容器，保留数据卷
docker compose down -v       # 停容器并删除 SQLite / Chroma / 上传数据
```

## 常见问题

1. **拉基础镜像失败（`docker.mirrors.ustc.edu.cn` DNS 失败）**  
   Docker Desktop → Settings → Docker Engine，检查 `registry-mirrors`：删掉失效镜像站，或改成可用源（如 `https://mirror.ccs.tencentyun.com`），Apply & Restart 后再执行 `docker compose up -d --build`。

2. **向量降级 / Embedding 失败**  
   检查 `.env` 中 Key 与 `OPENAI_BASE_URL` 是否可达（容器需能访问外网）。

3. **改了 `.env` 不生效**  
   `docker compose up -d --force-recreate backend`

4. **本机已有开发服务占 8520**  
   修改 `docker-compose.yml` 中 `8520:80` 左侧端口。

5. **与本地 `scripts/restart_dev.bat` 同时跑**  
   可以：Docker 不占用 8000/8001/5173；只需保证 8520 空闲。

## 发给组员（压缩包）

两种包，按网络情况选：

| 包 | 怎么生成 | 内容 | 何时用 |
|----|----------|------|--------|
| **配置包（小）** | `scripts\pack_docker.bat` | compose / Dockerfile / 说明 | 对方能拉基础镜像、或已有完整仓库 |
| **镜像包（大）** | 先 `docker compose build`，再 `scripts\pack_docker_images.bat` | `*.tar` 镜像 | 对方完全离线 / 拉不了镜像 |

生成物在项目根目录 `dist-docker\`。

**推荐给组员**：直接拉分支 `zhangyu-fix-final`（含 Docker 文件）+ 自备 `.env`，比只发零散 zip 更省事。
若只发配置包，对方仍需一份完整前后端源码才能 `build`。
