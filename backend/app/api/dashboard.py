"""系统概览统计 — 仅聚合现有库表与进程内缓存，不做假指标。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import config
from app.db.database import get_db
from app.db.models import Chunk, Conversation, Document, KnowledgeBase, User, UserGroup
from app.utils.auth import get_current_user
from app.utils.permission import ensure_admin_or_response
from app.utils.response import ok

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _is_today(value) -> bool:
    if value is None:
        return False
    today = _today_start_utc().date()
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date() == today
    text = str(value).strip()
    if not text:
        return False
    # 兼容 SQLite 字符串时间
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date() == today
    except ValueError:
        return text[:10] == today.isoformat()


def _probe_chroma() -> dict:
    """探测 Chroma：/api/v2/heartbeat，并兼容 localhost ↔ 127.0.0.1。"""
    from app.rag_engine.embedder import probe_chroma_heartbeat

    ok, detail, _host = probe_chroma_heartbeat()
    if ok:
        return {
            "key": "chroma",
            "label": "Chroma 向量服务",
            "status": "ok",
            "detail": detail,
        }
    msg = detail
    if "v1 API is deprecated" in msg or "Unimplemented" in msg:
        msg = "请改用 /api/v2/heartbeat（v1 已弃用）"
    elif "10061" in msg or "Connection refused" in msg or "积极拒绝" in msg:
        msg = (
            f"{config.CHROMA_HOST}:{config.CHROMA_PORT} 拒绝连接"
            "（确认已启动：chroma run --host 127.0.0.1 --port 8000；"
            ".env 中 CHROMA_HOST=127.0.0.1；或运行 scripts/restart_dev.bat）"
        )
    return {
        "key": "chroma",
        "label": "Chroma 向量服务",
        "status": "down",
        "detail": msg or "连接失败",
    }


def _probe_bm25_cache(kb_total: int) -> dict:
    try:
        from app.rag_engine.kb_index_cache import get_cached_kb_summary

        cached = get_cached_kb_summary()
        n = len(cached)
        status = "ok" if n > 0 else "idle"
        return {
            "key": "bm25_cache",
            "label": "BM25 内存索引",
            "status": status,
            "detail": f"已缓存 {n}/{kb_total} 个知识库",
            "cached_kb_count": n,
            "cached_kbs": cached[:8],
        }
    except Exception as e:  # noqa: BLE001
        return {
            "key": "bm25_cache",
            "label": "BM25 内存索引",
            "status": "down",
            "detail": str(e)[:120],
            "cached_kb_count": 0,
            "cached_kbs": [],
        }


async def _probe_rerank() -> dict:
    """探测 Rerank 微服务（组长端口表 8002）。"""
    from app.rag_engine.reranker import probe_rerank_service

    ok, detail, data = await probe_rerank_service()
    if ok:
        return {
            "key": "rerank",
            "label": "Rerank 重排服务",
            "status": "ok",
            "detail": detail,
            "mode": (data or {}).get("mode"),
            "model": (data or {}).get("model"),
        }
    return {
        "key": "rerank",
        "label": "Rerank 重排服务",
        "status": "down",
        "detail": detail or "8002 不可达",
    }


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    kb_count = db.query(KnowledgeBase).count()
    doc_count = db.query(Document).count()
    user_count = db.query(User).count()
    group_count = db.query(UserGroup).count()

    chunk_total = db.query(func.count(Chunk.id)).scalar() or 0
    chunk_sum_on_docs = db.query(func.coalesce(func.sum(Document.chunk_count), 0)).scalar() or 0
    if not chunk_total and chunk_sum_on_docs:
        chunk_total = int(chunk_sum_on_docs)

    # 文档状态 / 格式
    status_rows = (
        db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
    )
    docs_by_status = {str(s or "unknown"): int(c) for s, c in status_rows}

    type_rows = (
        db.query(Document.file_type, func.count(Document.id)).group_by(Document.file_type).all()
    )
    docs_by_file_type = {}
    for ft, c in type_rows:
        key = (str(ft or "unknown").strip().lower() or "unknown")
        docs_by_file_type[key] = docs_by_file_type.get(key, 0) + int(c)

    # 今日新增文档（按 created_at）
    today_new_docs = 0
    for (created_at,) in db.query(Document.created_at).all():
        if _is_today(created_at):
            today_new_docs += 1

    failed_total = (
        db.query(func.count(Document.id)).filter(Document.status == "failed").scalar() or 0
    )
    failed_docs = []
    for row in (
        db.query(Document)
        .filter(Document.status == "failed")
        .order_by(Document.created_at.desc())
        .limit(8)
        .all()
    ):
        failed_docs.append(
            {
                "id": row.id,
                "filename": row.filename or row.id,
                "kb_id": row.kb_id,
                "error_message": (row.error_message or "")[:160],
            }
        )

    # 对话运营（conversations）
    question_count = (
        db.query(func.count(Conversation.id)).filter(Conversation.role == "user").scalar() or 0
    )
    message_count = db.query(func.count(Conversation.id)).scalar() or 0
    session_count = (
        db.query(func.count(func.distinct(Conversation.session_id))).scalar() or 0
    )

    today_question_count = 0
    for (created_at,) in (
        db.query(Conversation.created_at).filter(Conversation.role == "user").all()
    ):
        if _is_today(created_at):
            today_question_count += 1

    # 会话轮次：按 session 的 user 消息数
    rounds_by_session: dict[str, int] = defaultdict(int)
    for sid, cnt in (
        db.query(Conversation.session_id, func.count(Conversation.id))
        .filter(Conversation.role == "user")
        .group_by(Conversation.session_id)
        .all()
    ):
        rounds_by_session[str(sid)] = int(cnt)

    avg_session_rounds = 0.0
    max_session_rounds = 0
    if rounds_by_session:
        vals = list(rounds_by_session.values())
        avg_session_rounds = round(sum(vals) / len(vals), 2)
        max_session_rounds = max(vals)

    avg_chunks_per_kb = round(chunk_total / kb_count, 2) if kb_count else 0.0

    services = [
        {
            "key": "api",
            "label": "后端 API",
            "status": "ok",
            "detail": "正常响应",
        },
        _probe_chroma(),
        await _probe_rerank(),
        _probe_bm25_cache(kb_count),
        {
            "key": "sqlite",
            "label": "会话存储",
            "status": "ok",
            "detail": f"消息 {message_count} 条 / 会话 {session_count} 个",
        },
    ]

    alerts = []
    for d in failed_docs:
        alerts.append(
            {
                "level": "error",
                "title": "文档解析失败",
                "message": f"{d['filename']}: {d['error_message'] or '未知错误'}",
            }
        )
    chroma = next((s for s in services if s["key"] == "chroma"), None)
    if chroma and chroma.get("status") == "down":
        alerts.insert(
            0,
            {
                "level": "warn",
                "title": "Chroma 不可用",
                "message": chroma.get("detail") or "向量检索将降级为关键词",
            },
        )
    if not alerts:
        alerts.append(
            {
                "level": "info",
                "title": "暂无异常",
                "message": "文档与向量服务当前未见失败记录",
            }
        )

    return ok(
        {
            "kb_count": kb_count,
            "doc_count": doc_count,
            "user_count": user_count,
            "group_count": group_count,
            "chunk_total": int(chunk_total),
            "avg_chunks_per_kb": avg_chunks_per_kb,
            "docs_by_status": docs_by_status,
            "docs_by_file_type": docs_by_file_type,
            "today_new_docs": today_new_docs,
            "failed_doc_count": int(failed_total),
            "failed_docs": failed_docs,
            "question_count": int(question_count),
            "message_count": int(message_count),
            "session_count": int(session_count),
            "today_question_count": today_question_count,
            "avg_session_rounds": avg_session_rounds,
            "max_session_rounds": int(max_session_rounds),
            "call_count": int(question_count),
            "services": services,
            "alerts": alerts[:10],
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
