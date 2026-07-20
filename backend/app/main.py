"""
FastAPI 入口
启动（port.md）：
  uvicorn app.main:app --host 0.0.0.0 --port 8001   # 主实例
  uvicorn app.main:app --host 0.0.0.0 --port 8003   # 副本1
  uvicorn app.main:app --host 0.0.0.0 --port 8004   # 副本2（可选）
"""

import os
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
    eval_tasks,
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
from app.schema.ports import DOCKER_SPA_PORT, GATEWAY_PORT, VITE_DEV_PORT

app = FastAPI(title="智能 RAG 平台 API", version="1.0.0")


def _cors_origins() -> list[str]:
    """允许的前端 / 网关来源（port.md：5173、8080、8520；5174 并行开发）。"""
    origins: list[str] = []
    for port in (VITE_DEV_PORT, 5174, GATEWAY_PORT, DOCKER_SPA_PORT):
        origins.extend(
            [
                f"http://localhost:{port}",
                f"http://127.0.0.1:{port}",
            ]
        )
    return origins


def _runtime_api_port() -> int:
    return int(os.getenv("API_PORT", str(config.API_PORT)))


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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
app.include_router(eval_tasks.router)
app.include_router(chat.router, prefix="/api/chat")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(kb.router)
app.include_router(docs.router)
app.include_router(models.router)
app.include_router(models.runtime_router)
app.include_router(user_groups.router)
app.include_router(branding.router)
app.include_router(dashboard.router)


def _reset_stale_processing_docs(max_age_minutes: int | None = None) -> int:
    """启动时把卡住的 processing 文档重置为 failed（按 updated_at，回退 created_at）。"""
    import sqlite3
    from datetime import datetime, timedelta, timezone

    from app.db.schema_compat import ensure_rag_schema

    minutes = int(
        max_age_minutes
        if max_age_minutes is not None
        else getattr(config, "STALE_PROCESSING_MINUTES", 30) or 30
    )
    db_path = Path(__file__).resolve().parents[2] / config.LOCAL_DB_NAME
    if not db_path.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    cutoff_s = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_rag_schema(conn)
        rows = conn.execute(
            "SELECT id, updated_at, created_at FROM documents WHERE status='processing'"
        ).fetchall()
        reset_ids = []
        for row in rows:
            ref = row["updated_at"] or row["created_at"]
            if not ref:
                reset_ids.append(row["id"])
                continue
            ref_s = str(ref).replace(" ", "T")[:19]
            if ref_s < cutoff_s:
                reset_ids.append(row["id"])
        if not reset_ids:
            return 0
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        for doc_id in reset_ids:
            conn.execute(
                """
                UPDATE documents
                SET status='failed',
                    error_message=?,
                    updated_at=?
                WHERE id=?
                """,
                ("处理超时已自动标记失败，请重新向量化", now, doc_id),
            )
        conn.commit()
        return len(reset_ids)
    finally:
        conn.close()


@app.on_event("startup")
async def startup():
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    try:
        db_file = Path(config.LOCAL_DB_NAME)
        if not db_file.is_absolute():
            db_file = Path(__file__).resolve().parents[2] / db_file
        db_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        from app.db.seed import init_schema_and_seed

        init_schema_and_seed()
        n = _reset_stale_processing_docs()
        if n:
            logger.warning("启动扫描：已重置 %s 条卡住的 processing 文档", n)
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


@app.get("/health")
@app.get("/api/health")
async def health():
    port = _runtime_api_port()
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "status": "ok",
            "env": config.ENV,
            "port": port,
            "collection": config.CHROMA_COLLECTION_NAME,
        },
    }
