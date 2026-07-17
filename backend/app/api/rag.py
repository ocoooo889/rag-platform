"""命中率测试接口 — 契约第八章（V2：文档状态准入 4002 + Langfuse 检索 Trace）"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.sqlite_helper import get_document, kb_exists, load_chunks_by_doc
from app.rag_engine.rag_pipeline import RAGPipeline
from app.schema.rag import HitTestRequest
from app.utils.response import fail, ok
from app.db.database import get_db
from app.utils.auth import get_current_user
from app.utils.permission import require_kb_access
from app.db.models import User

router = APIRouter(tags=["命中率测试"])

# 文档状态文案（V2 第十一章）
_STATUS_TEXT = {
    "pending": "等待处理",
    "processing": "正在处理中",
    "failed": "处理失败",
}


@router.post("/test_retrieve")
async def test_retrieve(req: HitTestRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    await require_kb_access(req.kb_id, user, db)
    if not (req.kb_id or "").strip():
        return fail(400, "缺少必填参数: kb_id")
    if not (req.doc_id or "").strip():
        return fail(400, "缺少必填参数: doc_id")
    if not (req.query or "").strip():
        return fail(400, "缺少必填参数: query")

    search_type = (req.search_type or "").strip().lower()
    if search_type not in {"vector", "keyword", "hybrid"}:
        return fail(400, "search_type 必须是 vector / keyword / hybrid")

    if not kb_exists(req.kb_id):
        return fail(404, "知识库不存在")

    doc = get_document(req.doc_id)
    if not doc or doc["kb_id"] != req.kb_id:
        return fail(404, "文档不存在或不属于该知识库")

    # V2：非 completed 不可检索 → 4002
    if doc["status"] != "completed":
        status_text = _STATUS_TEXT.get(doc["status"], "未就绪")
        return fail(
            4002,
            f"文档「{doc['filename']}」{status_text}，请等待处理完成后再试",
            data={"doc_id": req.doc_id, "status": doc["status"]},
        )

    rows = load_chunks_by_doc(req.doc_id)
    if not rows:
        return ok({
            "search_type": search_type,
            "total_hits": 0,
            "hits": [],
        })

    texts = [r["content"] for r in rows]
    ids = [r["chroma_id"] or r["id"] for r in rows]
    source_docs = [doc["filename"]] * len(rows)
    doc_ids = [req.doc_id] * len(rows)

    try:
        hits = await RAGPipeline.retrieve_only(
            query=req.query.strip(),
            texts=texts,
            ids=ids,
            search_type=search_type,
            top_n=req.top_n,
            kb_id=req.kb_id,
            doc_id=req.doc_id,
            source_docs=source_docs,
            doc_ids=doc_ids,
        )
    except Exception as e:
        return fail(5001, f"向量库服务异常: {e}")

    for h in hits:
        h.setdefault("source_doc", doc["filename"])
        h.setdefault("doc_id", req.doc_id)

    return ok({
        "search_type": search_type,
        "total_hits": len(hits),
        "hits": hits,
    })
