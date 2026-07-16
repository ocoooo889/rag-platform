"""智能对话接口 — 契约第九章（V2：文档准入 4002 + Langfuse 全链路）"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app import config
from app.db.sqlite_helper import (
    count_docs_by_kb,
    kb_exists,
    load_chat_history,
    load_chunks_by_kb,
    save_conversation,
)
from app.rag_engine.rag_pipeline import RAGPipeline
from app.schema.rag import ChatRequest
from app.utils.ids import new_id
from app.utils.langfuse_tracer import new_request_id
from app.utils.response import fail, ok

router = APIRouter(tags=["智能对话"])


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
async def chat_send(req: ChatRequest):
    if not (req.kb_id or "").strip():
        return fail(400, "缺少必填参数: kb_id")
    if not (req.query or "").strip():
        return fail(400, "缺少必填参数: query")
    if not kb_exists(req.kb_id):
        return fail(404, "知识库不存在")

    blocked = _check_kb_docs_ready(req.kb_id)
    if blocked is not None:
        return blocked

    session_id = req.session_id or new_id("s")
    texts, ids, source_docs, doc_ids = _prepare_chunk_rows(req.kb_id)
    history = _history_text(req.session_id)
    request_id = new_request_id()

    answer, refs = await RAGPipeline.query(
        kb_id=req.kb_id,
        query=req.query.strip(),
        search_type=req.search_type or "hybrid",
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

    if isinstance(answer, str) and answer.startswith("大模型服务暂时不可用"):
        return fail(5002, answer)

    save_conversation(new_id("msg"), session_id, req.kb_id, "user", req.query, None, _now())
    save_conversation(
        new_id("msg"), session_id, req.kb_id, "assistant", answer,
        json.dumps(refs, ensure_ascii=False), _now(),
    )

    return ok({
        "session_id": session_id,
        "answer": answer,
        "references": refs,
        "request_id": request_id,
    })


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    if not (req.kb_id or "").strip():
        return fail(400, "缺少必填参数: kb_id")
    if not (req.query or "").strip():
        return fail(400, "缺少必填参数: query")
    if not kb_exists(req.kb_id):
        return fail(404, "知识库不存在")

    blocked = _check_kb_docs_ready(req.kb_id)
    if blocked is not None:
        return blocked

    session_id = req.session_id or new_id("s")
    texts, ids, source_docs, doc_ids = _prepare_chunk_rows(req.kb_id)
    history = _history_text(req.session_id)
    request_id = new_request_id()

    token_iter, refs = await RAGPipeline.query(
        kb_id=req.kb_id,
        query=req.query.strip(),
        search_type=req.search_type or "hybrid",
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

    save_conversation(new_id("msg"), session_id, req.kb_id, "user", req.query, None, _now())

    async def event_gen():
        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id, 'request_id': request_id}, ensure_ascii=False)}\n\n"
        full = ""
        async for token in token_iter:
            full += token
            payload = {"type": "chunk", "content": token}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        save_conversation(
            new_id("msg"), session_id, req.kb_id, "assistant", full,
            json.dumps(refs, ensure_ascii=False), _now(),
        )
        done = {
            "type": "done",
            "content": "",
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
