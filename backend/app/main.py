"""
FastAPI 入口（3号先注册 rag/chat；4号后续挂 CRUD 路由）
启动：在 backend 目录执行
  uvicorn app.main:app --reload --port 8001
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import chat, rag

app = FastAPI(title="智能 RAG 平台 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag.router, prefix="/api/rag")
app.include_router(chat.router, prefix="/api/chat")


@app.on_event("startup")
async def startup():
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


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
