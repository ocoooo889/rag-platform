from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import KnowledgeBase, User, KbGroupAccess, Document, Chunk
from app.schema.request_schema import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user
from app.utils.permission import is_admin, get_user_accessible_kb_ids, ensure_admin_or_response
from app.utils.ids import new_id
from app.utils.logger import logger
from app.rag_engine.embedder import delete_from_chroma

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


def kb_to_dict(kb: KnowledgeBase):
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
        "document_count": len(kb.documents) if kb.documents else 0,
    }


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
    db.commit()
    return ResponseModel(msg="知识库删除成功")
