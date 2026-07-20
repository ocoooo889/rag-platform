import asyncio
import os
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document, KnowledgeBase, User
from app.schema.response_schema import ResponseModel
from app.api.auth import get_current_user
from app.utils.permission import require_kb_access, ensure_admin_or_response
from app.config import UPLOAD_DIR
from app.rag_engine.ingest import ingest_document
from app.rag_engine.embedder import delete_from_chroma
from app.rag_engine.splitter import list_split_strategies, parse_split_options
from app.utils.logger import logger
from app.utils.ids import new_id

router = APIRouter(prefix="/api", tags=["documents"])

# 同一 doc_id 防止重复触发 reprocess
_reprocess_inflight: set[str] = set()


async def _ingest_in_background(
    kb_id: str,
    doc_id: str,
    file_path: str,
    filename: str | None,
    split_options,
) -> None:
    """后台入库：异常只打日志，避免拖垮请求线程。"""
    try:
        await ingest_document(
            kb_id=kb_id,
            doc_id=doc_id,
            file_path=file_path,
            filename=filename,
            split_options=split_options,
        )
    except Exception:
        logger.exception("后台入库异常 doc_id=%s", doc_id)


class BatchDeleteRequest(BaseModel):
    ids: List[str] = Field(default_factory=list, min_length=1)


def doc_to_dict(doc: Document):
    updated = getattr(doc, "updated_at", None)
    return {
        "id": doc.id,
        "kb_id": doc.kb_id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "error_message": getattr(doc, "error_message", None) or "",
        "split_strategy": getattr(doc, "split_strategy", None) or "",
        "chunk_size": getattr(doc, "chunk_size", None),
        "chunk_overlap": getattr(doc, "chunk_overlap", None),
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": updated.isoformat() if updated else None,
    }


def _resolve_upload_path(doc: Document) -> str | None:
    """定位上传文件：优先 {id}_{filename}。"""
    candidates = [
        os.path.join(UPLOAD_DIR, f"{doc.id}_{doc.filename}"),
        os.path.join(UPLOAD_DIR, doc.filename or ""),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


async def _purge_document(db: Session, db_doc: Document) -> None:
    """删除单文档：Chroma 向量 + 本地文件 + DB 行。"""
    chroma_ids = [chunk.chroma_id for chunk in db_doc.chunks if chunk.chroma_id]
    if chroma_ids:
        try:
            await delete_from_chroma(chroma_ids)
            logger.info(
                "成功从 Chroma 删除文档 doc_id=%s 的 %s 个分片向量",
                db_doc.id,
                len(chroma_ids),
            )
        except Exception as e:
            logger.error("从 Chroma 向量库删除分片向量失败: %s", e)

    candidates = [
        os.path.join(UPLOAD_DIR, f"{db_doc.id}_{db_doc.filename}"),
        os.path.join(UPLOAD_DIR, db_doc.filename or ""),
    ]
    for file_path in candidates:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    db.delete(db_doc)


@router.get("/documents/split-strategies", response_model=ResponseModel)
async def get_split_strategies(
    current_user: User = Depends(get_current_user),
):
    """切分策略列表（前端下拉）。"""
    _ = current_user
    return ResponseModel(data={"items": list_split_strategies()})


@router.post("/knowledge-bases/{kb_id}/documents/upload", response_model=ResponseModel)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    split_strategy: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    parent_chunk_size: Optional[int] = Form(None),
    parent_chunk_overlap: Optional[int] = Form(None),
    semantic_threshold: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档到特定知识库。可选手动选择切分策略与参数。"""
    await require_kb_access(kb_id, current_user, db)

    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")

    if not file.filename.endswith((".md", ".txt")):
        return ResponseModel(code=400, msg="仅支持 .md 和 .txt 文件格式")

    split_options = parse_split_options(
        strategy=split_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        parent_chunk_size=parent_chunk_size,
        parent_chunk_overlap=parent_chunk_overlap,
        semantic_threshold=semantic_threshold,
    )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    doc_id = new_id("d")
    safe_name = os.path.basename(file.filename or "unnamed.txt")
    stored_name = f"{doc_id}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    try:
        with open(file_path, "wb") as buffer:
            import shutil

            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        return ResponseModel(code=500, msg=f"文件写入失败: {str(e)}")

    file_size = os.path.getsize(file_path)
    if file_size > 10 * 1024 * 1024:
        try:
            os.remove(file_path)
        except OSError:
            pass
        return ResponseModel(code=400, msg="文件大小超过 10MB 限制")

    file_type = "md" if safe_name.endswith(".md") else "txt"

    new_doc = Document(
        id=doc_id,
        kb_id=kb_id,
        filename=safe_name,
        file_type=file_type,
        file_size=file_size,
        status="pending",
        error_message=None,
        split_strategy=split_options.normalized_strategy(),
        chunk_size=split_options.resolved_size(),
        chunk_overlap=split_options.resolved_overlap(),
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 异步入库（create_task）：立刻返回上传结果；向量化在后台跑且不阻塞事件循环
    asyncio.create_task(
        _ingest_in_background(
            kb_id=kb_id,
            doc_id=new_doc.id,
            file_path=file_path,
            filename=file.filename,
            split_options=split_options,
        )
    )

    return ResponseModel(data=doc_to_dict(new_doc))


@router.get("/knowledge-bases/{kb_id}/documents", response_model=ResponseModel)
async def get_documents(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定知识库下的所有文档列表，内置权限校验"""
    await require_kb_access(kb_id, current_user, db)
    docs = db.query(Document).filter(Document.kb_id == kb_id).all()
    return ResponseModel(data=[doc_to_dict(d) for d in docs])


@router.post("/documents/{doc_id}/reprocess", response_model=ResponseModel)
async def reprocess_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新向量化：具备知识库访问权即可。processing / 进行中任务直接拒绝。"""
    from datetime import datetime, timezone

    db_doc = db.query(Document).filter(Document.id == doc_id).first()
    if not db_doc:
        return ResponseModel(code=404, msg="文档不存在")

    await require_kb_access(db_doc.kb_id, current_user, db)

    if db_doc.status == "processing" or doc_id in _reprocess_inflight:
        return ResponseModel(
            code=400,
            msg="文档正在处理中，请稍后再试",
            data={"doc_id": doc_id, "status": db_doc.status},
        )

    file_path = _resolve_upload_path(db_doc)
    if not file_path:
        return ResponseModel(code=404, msg="原始文件不存在，无法重新处理")

    _reprocess_inflight.add(doc_id)
    try:
        # 清理旧向量与切片，重置为 pending
        chroma_ids = [c.chroma_id for c in db_doc.chunks if c.chroma_id]
        if chroma_ids:
            try:
                await delete_from_chroma(chroma_ids)
            except Exception as e:
                logger.warning("reprocess 清理 Chroma 忽略: %s", e)

        for chunk in list(db_doc.chunks):
            db.delete(chunk)

        db_doc.status = "pending"
        db_doc.chunk_count = 0
        db_doc.error_message = None
        if hasattr(db_doc, "updated_at"):
            db_doc.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_doc)

        async def _job():
            try:
                await ingest_document(
                    kb_id=db_doc.kb_id,
                    doc_id=db_doc.id,
                    file_path=file_path,
                    filename=db_doc.filename,
                )
            finally:
                _reprocess_inflight.discard(doc_id)

        background_tasks.add_task(_job)
    except Exception:
        _reprocess_inflight.discard(doc_id)
        raise

    return ResponseModel(msg="已开始重新处理", data=doc_to_dict(db_doc))


@router.delete("/documents/{doc_id}", response_model=ResponseModel)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档（仅管理员）。"""
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_doc = db.query(Document).filter(Document.id == doc_id).first()
    if not db_doc:
        return ResponseModel(code=404, msg="文档不存在")

    await require_kb_access(db_doc.kb_id, current_user, db)
    await _purge_document(db, db_doc)
    db.commit()
    return ResponseModel(msg="文档删除成功")


@router.post("/documents/batch-delete", response_model=ResponseModel)
async def batch_delete_documents(
    body: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除文档（仅管理员）。"""
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    ids = [str(i).strip() for i in (body.ids or []) if str(i).strip()]
    if not ids:
        return ResponseModel(code=400, msg="请选择要删除的文档")

    docs = db.query(Document).filter(Document.id.in_(ids)).all()
    if not docs:
        return ResponseModel(code=404, msg="未找到可删除的文档")

    # 按知识库做权限校验（去重 kb）
    checked_kb = set()
    for doc in docs:
        if doc.kb_id in checked_kb:
            continue
        await require_kb_access(doc.kb_id, current_user, db)
        checked_kb.add(doc.kb_id)

    deleted = 0
    for doc in docs:
        await _purge_document(db, doc)
        deleted += 1
    db.commit()
    return ResponseModel(msg=f"成功删除 {deleted} 个文档", data={"deleted": deleted})
