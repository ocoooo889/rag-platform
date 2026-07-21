"""命中率测试接口 — 契约第八章（V2：文档状态准入 4002 + Langfuse 检索 Trace）"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.db.sqlite_helper import get_document, kb_exists, load_chunks_by_doc
from app.rag_engine.rag_pipeline import RAGPipeline
from app.rag_engine.content_moderation import check_user_query
from app.schema.rag import HitTestRequest
from app.utils.auth import get_current_user
from app.utils.permission import require_kb_access
from app.utils.response import fail, ok

router = APIRouter(tags=["命中率测试"])

# 文档状态文案（V2 第十一章）
_STATUS_TEXT = {
    "pending": "等待处理",
    "processing": "正在处理中",
    "failed": "处理失败",
    "degraded": "仅关键词可用（向量未就绪）",
}

# 可检索：completed / degraded；纯向量仅 completed
_RETRIEVABLE = {"completed", "degraded"}


def _resolve_doc_ids(req: HitTestRequest) -> list[str]:
    """合并 doc_id / doc_ids，去重且保序"""
    ids: list[str] = []
    seen: set[str] = set()

    def _add(raw: str | None) -> None:
        did = (raw or "").strip()
        if not did or did in seen:
            return
        seen.add(did)
        ids.append(did)

    if req.doc_ids:
        for item in req.doc_ids:
            _add(item if isinstance(item, str) else str(item))
    _add(req.doc_id)
    return ids


async def _retrieve_one_doc(
    *,
    kb_id: str,
    doc_id: str,
    query: str,
    search_type: str,
    top_n: int,
    enable_rerank: bool | None = None,
):
    """
    单文档检索（保留原有准入与返回逻辑）。
    成功返回 (None, hits, meta)；业务失败返回 (fail_response, None, None)。
    """
    doc = get_document(doc_id)
    if not doc or doc["kb_id"] != kb_id:
        return fail(404, "文档不存在或不属于该知识库"), None, None

    status = doc["status"]
    # pending / processing / failed → 4002
    if status not in _RETRIEVABLE:
        status_text = _STATUS_TEXT.get(status, "未就绪")
        return (
            fail(
                4002,
                f"文档「{doc['filename']}」{status_text}，请等待处理完成后再试",
                data={"doc_id": doc_id, "status": status},
            ),
            None,
        )

    # degraded + 纯向量 → 4004（4003 已用于白标配置）
    if status == "degraded" and search_type == "vector":
        return (
            fail(
                4004,
                f"文档「{doc['filename']}」仅关键词可用，请改用关键词或混合检索，或重新向量化",
                data={"doc_id": doc_id, "status": status},
            ),
            None,
            None,
        )

    rows = load_chunks_by_doc(doc_id)
    if not rows:
        return None, [], {}

    texts = [r["content"] for r in rows]
    ids = [r["chroma_id"] or r["id"] for r in rows]
    source_docs = [doc["filename"]] * len(rows)
    doc_ids = [doc_id] * len(rows)

    try:
        hits, retrieve_meta = await RAGPipeline.retrieve_only(
            query=query,
            texts=texts,
            ids=ids,
            search_type=search_type,
            top_n=top_n,
            kb_id=kb_id,
            doc_id=doc_id,
            source_docs=source_docs,
            doc_ids=doc_ids,
            enable_rerank=enable_rerank,
        )
    except Exception as e:
        return fail(5001, f"向量库服务异常: {e}"), None, None

    for h in hits:
        h.setdefault("source_doc", doc["filename"])
        h.setdefault("doc_id", doc_id)
    return None, hits, retrieve_meta


@router.post("/test_retrieve")
async def test_retrieve(
    req: HitTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (req.kb_id or "").strip():
        return fail(400, "缺少必填参数: kb_id")
    if not (req.query or "").strip():
        return fail(400, "缺少必填参数: query")

    ok_flag, sens_msg = check_user_query(req.query)
    if not ok_flag:
        return fail(400, sens_msg)

    target_ids = _resolve_doc_ids(req)
    if not target_ids:
        return fail(400, "缺少必填参数: doc_id 或 doc_ids")

    search_type = (req.search_type or "").strip().lower()
    if search_type not in {"vector", "keyword", "hybrid"}:
        return fail(400, "search_type 必须是 vector / keyword / hybrid")

    # V2 第七章：先鉴权再检索（admin 放行；越权 403）
    await require_kb_access(req.kb_id, current_user, db)

    if not kb_exists(req.kb_id):
        return fail(404, "知识库不存在")

    query = req.query.strip()
    top_n = req.top_n

    # 单文档：行为与原先完全一致（含 404 / 4002 直接返回）
    if len(target_ids) == 1:
        err, hits, retrieve_meta = await _retrieve_one_doc(
            kb_id=req.kb_id,
            doc_id=target_ids[0],
            query=query,
            search_type=search_type,
            top_n=top_n,
            enable_rerank=req.enable_rerank,
        )
        if err is not None:
            return err
        return ok({
            "search_type": search_type,
            "total_hits": len(hits),
            "hits": hits,
            "meta": retrieve_meta or {},
        })

    # 多文档：逐篇检索后按 score 合并，截断 top_n；遇 404/4002/5001 立即返回
    merged: list[dict] = []
    merged_meta: dict = {}
    for doc_id in target_ids:
        err, hits, retrieve_meta = await _retrieve_one_doc(
            kb_id=req.kb_id,
            doc_id=doc_id,
            query=query,
            search_type=search_type,
            top_n=top_n,
            enable_rerank=req.enable_rerank,
        )
        if err is not None:
            return err
        merged.extend(hits or [])
        if retrieve_meta:
            merged_meta = retrieve_meta

    merged.sort(key=lambda h: float(h.get("score") or 0), reverse=True)
    hits = merged[:top_n]
    return ok({
        "search_type": search_type,
        "total_hits": len(hits),
        "hits": hits,
        "meta": merged_meta,
    })
