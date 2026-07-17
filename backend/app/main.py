"""
FastAPI 入口（3号先注册 rag/chat；4号后续挂 CRUD 路由）
启动：在 backend 目录执行
  uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

端口约定：
  - FastAPI API：8001（与 frontend Vite 代理一致）
  - Chroma 向量库：8000（勿与 API 混用）
"""

import time
import uuid
import sys
import subprocess
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app import config
from app.api import (
    chat, rag, auth, users, roles, kb, docs, models, user_groups, branding, dashboard
)
from app.utils.logger import logger, request_id_var, action_var

app = FastAPI(title="智能 RAG 平台 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)
    action_var.set(f"{request.method} {request.url.path}")
    
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={
            "duration_ms": round(duration_ms, 2),
            "request_id": req_id
        }
    )
    return response

# 挂载 Prometheus 监控
Instrumentator().instrument(app).expose(app)

app.include_router(rag.router, prefix="/api/rag")
app.include_router(chat.router, prefix="/api/chat")
# 以下路由模块自身已带完整 /api/... 前缀，勿再套一层
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(kb.router)
app.include_router(docs.router)
app.include_router(models.router)
app.include_router(user_groups.router)
app.include_router(branding.router)
app.include_router(dashboard.router, prefix="/api/dashboard")


@app.on_event("startup")
async def startup():
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    # 初始化数据库种子
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "init_db.py"
    if script_path.exists():
        subprocess.run([sys.executable, str(script_path)], check=True)
    else:
        logger.warning(f"init_db.py not found at {script_path}")


@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "status": "ok",
            "env": config.ENV,
            "collection": config.CHROMA_COLLECTION_NAME,
        },
    }
