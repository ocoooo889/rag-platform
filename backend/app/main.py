"""
FastAPI 入口
启动：在 backend 目录执行
  uvicorn app.main:app --reload --port 8001
"""

import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app import config
from app.api import (
    chat,
    rag,
    rag_eval,
    auth,
    users,
    roles,
    kb,
    docs,
    models,
    user_groups,
    branding,
    dashboard,
)
from app.utils.exceptions import BusinessException
from app.utils.logger import logger, request_id_var, action_var

app = FastAPI(title="智能 RAG 平台 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "msg": exc.msg, "data": None},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "请求错误"
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": msg, "data": None},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)
    action_var.set(f"{request.method} {request.url.path}")

    # 流式接口：不做耗时统计包一层，避免中间件语义干扰排查
    if request.url.path.rstrip("/").endswith("/chat/stream"):
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={"duration_ms": round(duration_ms, 2), "request_id": req_id},
    )
    return response


Instrumentator(
    should_exclude_streaming_duration=True,
    excluded_handlers=["/metrics", "/api/chat/stream", "/api/health", "/health"],
).instrument(app).expose(app)

# 白标与上传静态资源（相对 backend 工作目录）
_uploads_root = Path("uploads").resolve()
_uploads_root.mkdir(parents=True, exist_ok=True)
(_uploads_root / "branding").mkdir(parents=True, exist_ok=True)
(_uploads_root / "avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_root)), name="uploads")

app.include_router(rag.router, prefix="/api/rag")
app.include_router(rag_eval.router, prefix="/api/rag")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(kb.router)
app.include_router(docs.router)
app.include_router(models.router)
app.include_router(user_groups.router)
app.include_router(branding.router)
app.include_router(dashboard.router)


@app.on_event("startup")
async def startup():
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    try:
        from app.db.seed import init_schema_and_seed

        init_schema_and_seed()
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


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
