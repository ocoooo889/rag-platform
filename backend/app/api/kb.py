from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import KnowledgeBase, User, KbGroupAccess
from app.schema.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate, ResponseModel
from app.utils.auth import get_current_user
from app.utils.permission import is_admin, get_user_accessible_kb_ids

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])

def kb_to_dict(kb: KnowledgeBase):
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
        "document_count": len(kb.documents) if kb.documents else 0
    }

@router.post("", response_model=ResponseModel)
def create_kb(
    kb: KnowledgeBaseCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """创建知识库，并可选择性地直接授权给某些用户组"""
    new_kb = KnowledgeBase(name=kb.name, description=kb.description)
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    
    # V2 新增：支持创建知识库时同步指定绑定的用户组授权
    if kb.group_ids:
        for gid in kb.group_ids:
            db.add(KbGroupAccess(kb_id=new_kb.id, group_id=gid))
        db.commit()
        db.refresh(new_kb)
        
    return ResponseModel(data=kb_to_dict(new_kb))

@router.get("", response_model=ResponseModel)
async def get_kbs(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """获取可访问的知识库列表。
    - admin 直接返回全部；
    - 非 admin 仅返回所属用户组被授权的知识库；
    - 若无任何授权知识库或未分配用户组，则返回状态码 4001。
    """
    if is_admin(current_user):
        kbs = db.query(KnowledgeBase).all()
        return ResponseModel(data=[kb_to_dict(kb) for kb in kbs])
    
    accessible_ids = await get_user_accessible_kb_ids(db, current_user.id)
    if not accessible_ids:
        return ResponseModel(
            code=4001, 
            msg="您尚未被分配到任何用户组，或所属用户组尚未授权任何知识库，请联系管理员",
            data=[]
        )
        
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(accessible_ids)).all()
    return ResponseModel(data=[kb_to_dict(kb) for kb in kbs])

@router.put("/{kb_id}", response_model=ResponseModel)
def update_kb(
    kb_id: int, 
    kb: KnowledgeBaseUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """修改知识库元数据"""
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
def delete_kb(
    kb_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """删除知识库（包括其下属所有文档和关联记录）"""
    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")
    
    db.delete(db_kb)
    db.commit()
    return ResponseModel(msg="知识库删除成功")
