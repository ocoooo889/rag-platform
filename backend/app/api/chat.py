"""智能对话接口 — 契约第九章（V2：文档准入 4002 + Langfuse 全链路）"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import config
from app.db.database import get_db
from app.db.models import User
from app.db.sqlite_helper import (
    count_docs_by_kb,
    delete_chat_session,
    get_session_kb_id,
    kb_exists,
    list_chat_messages,
    list_chat_sessions,
    load_chat_history,
    load_chunks_by_kb,
    save_conversation,
)
from app.rag_engine.rag_pipeline import RAGPipeline
from app.schema.rag import ChatRequest
from app.utils.auth import get_current_user
from app.utils.ids import new_id
from app.utils.langfuse_tracer import new_request_id
from app.utils.llm_client import LLMServiceError
from app.utils.permission import require_kb_access
from app.utils.response import fail, ok

router = APIRouter(tags=["智能对话"])

_VALID_SEARCH_TYPES = frozenset({"vector", "keyword", "hybrid"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _history_text(session_id: str | None) -> str:
    if not session_id:
        return ""
    rows = load_chat_history(session_id, config.MAX_CHAT_HISTORY_ROUNDS)
    if not rows:
        return ""
    return "\n".join(f"{r['role']}: {r['content']}" for r in rows)


def _check_kb_docs_ready(kb_id: str):
    """
    V2 第十一章：知识库文档准入。
    - 无文档 → 404
    - 全部未 completed → 4002
    - 部分 completed → 放行（检索层只取 completed）
    """
    total, pending = count_docs_by_kb(kb_id)
    if total == 0:
        return fail(404, "该知识库下暂无可用文档")
    if pending > 0 and total == pending:
        return fail(
            4002,
            f"知识库下 {pending} 篇文档正在处理中，请等待处理完成后再试",
        )
    return None


def _validate_search_type(search_type: str | None) -> str | None:
    """校验 search_type；非法返回错误响应，合法返回规范化值"""
    st = (search_type or "hybrid").strip().lower() or "hybrid"
    if st not in _VALID_SEARCH_TYPES:
        return None
    return st


def _prepare_chunk_rows(kb_id: str):
    rows = load_chunks_by_kb(kb_id)
    if not rows:
        return [], [], [], []
    texts = [r["content"] for r in rows]
    ids = [r["chroma_id"] or r["id"] for r in rows]
    source_docs = [r["filename"] if "filename" in r.keys() else "" for r in rows]
    doc_ids = [r["doc_id"] for r in rows]
    return texts, ids, source_docs, doc_ids


@router.post("/send")
async def chat_send(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (req.kb_id or "").strip():
        return fail(400, "缺少必填参数: kb_id")
    if not (req.query or "").strip():
        return fail(400, "缺少必填参数: query")

    search_type = _validate_search_type(req.search_type)
    if search_type is None:
        return fail(400, "search_type 必须是 vector / keyword / hybrid")

    # V2 第七章：先鉴权再对话
    await require_kb_access(req.kb_id, current_user, db)

    if not kb_exists(req.kb_id):
        return fail(404, "知识库不存在")

    blocked = _check_kb_docs_ready(req.kb_id)
    if blocked is not None:
        return blocked

    session_id = req.session_id or new_id("s")
    texts, ids, source_docs, doc_ids = _prepare_chunk_rows(req.kb_id)
    history = _history_text(req.session_id)
    request_id = new_request_id()
    query = req.query.strip()

    try:
        answer, refs = await RAGPipeline.query(
            kb_id=req.kb_id,
            query=query,
            search_type=search_type,
            texts=texts,
            ids=ids,
            top_n=req.top_n,
            source_docs=source_docs,
            doc_ids=doc_ids,
            chat_history=history,
            session_id=session_id,
            stream=False,
            request_id=request_id,
        )
    except LLMServiceError as e:
        return fail(5002, e.message)

    save_conversation(new_id("msg"), session_id, req.kb_id, "user", query, None, _now())
    save_conversation(
        new_id("msg"), session_id, req.kb_id, "assistant", answer,
        json.dumps(refs, ensure_ascii=False), _now(),
    )

    # V2 契约：响应回显 query（CHAT-22 / BUG-04）
    return ok({
        "session_id": session_id,
        "query": query,
        "answer": answer,
        "references": refs,
        "request_id": request_id,
    })


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (req.kb_id or "").strip():
        return fail(400, "缺少必填参数: kb_id")
    if not (req.query or "").strip():
        return fail(400, "缺少必填参数: query")

    search_type = _validate_search_type(req.search_type)
    if search_type is None:
        return fail(400, "search_type 必须是 vector / keyword / hybrid")

    # V2 第七章：先鉴权再对话
    await require_kb_access(req.kb_id, current_user, db)

    if not kb_exists(req.kb_id):
        return fail(404, "知识库不存在")

    blocked = _check_kb_docs_ready(req.kb_id)
    if blocked is not None:
        return blocked

    session_id = req.session_id or new_id("s")
    texts, ids, source_docs, doc_ids = _prepare_chunk_rows(req.kb_id)
    history = _history_text(req.session_id)
    request_id = new_request_id()
    query = req.query.strip()

    try:
        token_iter, refs = await RAGPipeline.query(
            kb_id=req.kb_id,
            query=query,
            search_type=search_type,
            texts=texts,
            ids=ids,
            top_n=req.top_n,
            source_docs=source_docs,
            doc_ids=doc_ids,
            chat_history=history,
            session_id=session_id,
            stream=True,
            request_id=request_id,
        )
    except LLMServiceError as e:
        return fail(5002, e.message)

    save_conversation(new_id("msg"), session_id, req.kb_id, "user", query, None, _now())

    async def event_gen():
        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id, 'request_id': request_id, 'query': query}, ensure_ascii=False)}\n\n"
        full = ""
        try:
            async for token in token_iter:
                full += token
                payload = {"type": "chunk", "content": token}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except LLMServiceError as e:
            # 流已开始时用 chunk 推送错误文案，仍结束 done
            err = e.message
            full = err
            yield f"data: {json.dumps({'type': 'chunk', 'content': err}, ensure_ascii=False)}\n\n"

        save_conversation(
            new_id("msg"), session_id, req.kb_id, "assistant", full,
            json.dumps(refs, ensure_ascii=False), _now(),
        )
        done = {
            "type": "done",
            "content": "",
            "query": query,
            "references": [
                {
                    "chunk_id": r.get("chunk_id"),
                    "content": r.get("content"),
                    "score": r.get("score"),
                }
                for r in refs
            ],
        }
        yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def _parse_references(raw) -> list | None:
    """解析 messages.references JSON；无值或非法时返回 None（不出现在 user 消息）"""
    if raw is None or raw == "":
        return None
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else None
    except (TypeError, json.JSONDecodeError):
        return None


@router.get("/sessions")
async def chat_sessions(
    kb_id: str = Query(..., description="知识库 ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GET /api/chat/sessions — 按知识库分页列出会话"""
    kb_id = (kb_id or "").strip()
    if not kb_id:
        return fail(400, "缺少必填参数: kb_id")

    await require_kb_access(kb_id, current_user, db)

    if not kb_exists(kb_id):
        return fail(404, "知识库不存在")

    items, total = list_chat_sessions(kb_id, page=page, page_size=page_size)
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/sessions/{session_id}/messages")
async def chat_session_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GET /api/chat/sessions/{session_id}/messages — 会话消息历史"""
    session_id = (session_id or "").strip()
    if not session_id:
        return fail(400, "缺少必填参数: session_id")

    kb_id = get_session_kb_id(session_id)
    if not kb_id:
        return fail(404, "会话不存在")

    await require_kb_access(kb_id, current_user, db)

    rows, total = list_chat_messages(session_id, page=page, page_size=page_size)
    items = []
    for r in rows:
        item = {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "created_at": r["created_at"],
        }
        refs = _parse_references(r["references"] if "references" in r.keys() else None)
        if refs is not None and r["role"] == "assistant":
            item["references"] = refs
        items.append(item)

    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.delete("/sessions/{session_id}")
async def chat_session_delete(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """DELETE /api/chat/sessions/{session_id} — 删除会话（级联删除消息）"""
    session_id = (session_id or "").strip()
    if not session_id:
        return fail(400, "缺少必填参数: session_id")

    kb_id = get_session_kb_id(session_id)
    if not kb_id:
        return fail(404, "会话不存在")

    await require_kb_access(kb_id, current_user, db)

    delete_chat_session(session_id)
    return ok(None)
