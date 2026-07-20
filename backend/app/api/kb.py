import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app import config
from app.api import docs as docs_api
from app.db.database import get_db
from app.db.models import KnowledgeBase, User, KbGroupAccess, Document, Chunk, SystemConfig
from app.rag_engine.embedder import delete_from_chroma
from app.rag_engine.ingest import ingest_document
from app.schema.request_schema import KnowledgeBaseCreate, KnowledgeBaseUpdate, KbIndexConfigUpdate
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user
from app.utils.ids import new_id
from app.utils.logger import logger
from app.utils.permission import is_admin, get_user_accessible_kb_ids, ensure_admin_or_response, require_kb_access

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])

_INDEX_CONFIG_PREFIX = "kb_index_config:"
_VALID_SEARCH_TYPES = {"vector", "keyword", "hybrid"}


def kb_to_dict(kb: KnowledgeBase):
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
        "document_count": len(kb.documents) if kb.documents else 0,
    }


def _index_config_key(kb_id: str) -> str:
    return f"{_INDEX_CONFIG_PREFIX}{kb_id}"


def _default_index_config(kb_id: str) -> dict:
    return {
        "kb_id": kb_id,
        "chunk_size": config.CHUNK_SIZE,
        "chunk_overlap": config.CHUNK_OVERLAP,
        "hybrid_alpha": config.HYBRID_ALPHA,
        "default_search_type": "hybrid",
        "enable_rerank": False,
        "default_top_n": config.DEFAULT_TOP_N,
        "updated_at": None,
    }


def _parse_index_config(raw: str | None, kb_id: str) -> dict:
    base = _default_index_config(kb_id)
    if not raw:
        return base
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("知识库 index-config JSON 损坏 kb_id=%s，使用默认值", kb_id)
        return base
    if not isinstance(data, dict):
        return base
    for key in (
        "chunk_size",
        "chunk_overlap",
        "hybrid_alpha",
        "default_search_type",
        "enable_rerank",
        "default_top_n",
        "updated_at",
    ):
        if key in data and data[key] is not None:
            base[key] = data[key]
    st = str(base.get("default_search_type") or "hybrid").strip().lower()
    base["default_search_type"] = st if st in _VALID_SEARCH_TYPES else "hybrid"
    base["enable_rerank"] = bool(base.get("enable_rerank"))
    return base


def _load_index_config(db: Session, kb_id: str) -> dict:
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.config_key == _index_config_key(kb_id))
        .first()
    )
    return _parse_index_config(row.config_value if row else None, kb_id)


def _save_index_config(db: Session, kb_id: str, payload: dict) -> dict:
    merged = _load_index_config(db, kb_id)
    merged.update(payload)
    merged["kb_id"] = kb_id
    merged["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    st = str(merged.get("default_search_type") or "hybrid").strip().lower()
    if st not in _VALID_SEARCH_TYPES:
        raise ValueError("default_search_type 须为 vector / keyword / hybrid")

    chunk_size = int(merged["chunk_size"])
    chunk_overlap = int(merged["chunk_overlap"])
    if chunk_size < 100 or chunk_size > 2000:
        raise ValueError("chunk_size 须在 100~2000 之间")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 须在 0 至 chunk_size 之间")

    alpha = float(merged["hybrid_alpha"])
    if alpha < 0.0 or alpha > 1.0:
        raise ValueError("hybrid_alpha 须在 0~1 之间")

    top_n = int(merged["default_top_n"])
    if top_n < 1 or top_n > config.MAX_TOP_N:
        raise ValueError(f"default_top_n 须在 1~{config.MAX_TOP_N} 之间")

    merged["default_search_type"] = st
    merged["enable_rerank"] = bool(merged.get("enable_rerank"))

    key = _index_config_key(kb_id)
    row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    text = json.dumps(merged, ensure_ascii=False)
    if row:
        row.config_value = text
    else:
        db.add(SystemConfig(config_key=key, config_value=text))
    db.commit()
    return merged


async def _queue_doc_rebuild(
    db: Session, db_doc: Document, background_tasks: BackgroundTasks
) -> str:
    """返回 queued | skipped_processing | skipped_missing_file"""
    if db_doc.status == "processing" or db_doc.id in docs_api._reprocess_inflight:
        return "skipped_processing"

    file_path = docs_api._resolve_upload_path(db_doc)
    if not file_path:
        return "skipped_missing_file"

    docs_api._reprocess_inflight.add(db_doc.id)
    try:
        chroma_ids = [c.chroma_id for c in db_doc.chunks if c.chroma_id]
        if chroma_ids:
            try:
                await delete_from_chroma(chroma_ids)
            except Exception as exc:  # noqa: BLE001
                logger.warning("rebuild 清理 Chroma 忽略 doc_id=%s: %s", db_doc.id, exc)

        for chunk in list(db_doc.chunks):
            db.delete(chunk)

        db_doc.status = "pending"
        db_doc.chunk_count = 0
        db_doc.error_message = None
        if hasattr(db_doc, "updated_at"):
            db_doc.updated_at = datetime.now(timezone.utc)

        async def _job():
            try:
                await ingest_document(
                    kb_id=db_doc.kb_id,
                    doc_id=db_doc.id,
                    file_path=file_path,
                    filename=db_doc.filename,
                )
            finally:
                docs_api._reprocess_inflight.discard(db_doc.id)

        background_tasks.add_task(_job)
        return "queued"
    except Exception:
        docs_api._reprocess_inflight.discard(db_doc.id)
        raise


@router.post("", response_model=ResponseModel)
def create_kb(
    kb: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    new_kb = KnowledgeBase(id=new_id("kb"), name=kb.name, description=kb.description)
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)

    if kb.group_ids:
        for gid in kb.group_ids:
            db.add(KbGroupAccess(kb_id=new_kb.id, group_id=gid))
        db.commit()
        db.refresh(new_kb)

    return ResponseModel(data=kb_to_dict(new_kb))


@router.get("", response_model=ResponseModel)
async def get_kbs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if is_admin(current_user):
        kbs = db.query(KnowledgeBase).all()
        return ResponseModel(data=[kb_to_dict(kb) for kb in kbs])

    accessible_ids = await get_user_accessible_kb_ids(db, current_user.id)
    if not accessible_ids:
        return ResponseModel(
            code=4001,
            msg="您尚未被分配到任何用户组，或所属用户组尚未授权任何知识库，请联系管理员",
            data=[],
        )

    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(accessible_ids)).all()
    return ResponseModel(data=[kb_to_dict(kb) for kb in kbs])


@router.put("/{kb_id}", response_model=ResponseModel)
def update_kb(
    kb_id: str,
    kb: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")

    if kb.name is not None:
        db_kb.name = kb.name
    if kb.description is not None:
        db_kb.description = kb.description

    db.commit()
    db.refresh(db_kb)
    return ResponseModel(data=kb_to_dict(db_kb))


@router.delete("/{kb_id}", response_model=ResponseModel)
async def delete_kb(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")

    # 先清 Chroma，再删库（级联 documents/chunks）
    doc_ids = [
        row[0]
        for row in db.query(Document.id).filter(Document.kb_id == kb_id).all()
    ]
    if doc_ids:
        chroma_ids = [
            c.chroma_id
            for c in db.query(Chunk).filter(Chunk.doc_id.in_(doc_ids)).all()
            if c.chroma_id
        ]
        if chroma_ids:
            try:
                await delete_from_chroma(chroma_ids)
                logger.info(
                    f"删除知识库 kb_id={kb_id} 时清理 Chroma 分片 {len(chroma_ids)} 个"
                )
            except Exception as e:
                logger.error(f"删除知识库时清理 Chroma 失败 kb_id={kb_id}: {e}")

    db.delete(db_kb)
    db.query(SystemConfig).filter(
        SystemConfig.config_key == _index_config_key(kb_id)
    ).delete(synchronize_session=False)
    db.commit()
    return ResponseModel(msg="知识库删除成功")


@router.get("/{kb_id}/index-config", response_model=ResponseModel)
async def get_kb_index_config(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库级索引配置（需知识库访问权）。"""
    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")

    await require_kb_access(kb_id, current_user, db)
    return ResponseModel(data=_load_index_config(db, kb_id))


@router.put("/{kb_id}/index-config", response_model=ResponseModel)
async def update_kb_index_config(
    kb_id: str,
    body: KbIndexConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新知识库级索引配置（仅管理员）。"""
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return ResponseModel(code=400, msg="请至少提供一个配置项")

    try:
        saved = _save_index_config(db, kb_id, patch)
    except ValueError as exc:
        return ResponseModel(code=400, msg=str(exc))

    logger.info("更新知识库 index-config kb_id=%s", kb_id)
    return ResponseModel(data=saved)


@router.post("/{kb_id}/rebuild", response_model=ResponseModel)
async def rebuild_kb_index(
    kb_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    重建知识库索引：对该库下全部文档重新切片并向量化（仅管理员）。
    正在 processing 的文档会跳过；缺原始文件的文档会跳过。
    """
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")

    docs = db.query(Document).filter(Document.kb_id == kb_id).all()
    queued: list[str] = []
    skipped_processing: list[str] = []
    skipped_missing_file: list[str] = []

    for doc in docs:
        result = await _queue_doc_rebuild(db, doc, background_tasks)
        if result == "queued":
            queued.append(doc.id)
        elif result == "skipped_processing":
            skipped_processing.append(doc.id)
        else:
            skipped_missing_file.append(doc.id)

    db.commit()

    return ResponseModel(
        msg="已开始重建索引",
        data={
            "kb_id": kb_id,
            "total": len(docs),
            "queued": len(queued),
            "skipped_processing": len(skipped_processing),
            "skipped_missing_file": len(skipped_missing_file),
            "queued_doc_ids": queued,
            "skipped_processing_doc_ids": skipped_processing,
            "skipped_missing_file_doc_ids": skipped_missing_file,
        },
    )
