from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import User, UserGroup, UserGroupMember, KbGroupAccess, KnowledgeBase
from app.schema.schemas import (
    ResponseModel, 
    UserGroupCreate, 
    UserGroupOut, 
    GroupMembersAdd, 
    GroupKbAccess
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/user-groups", tags=["user-groups"])

def group_to_dict(group: UserGroup):
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "member_count": len(group.members) if group.members else 0,
        "kb_count": len(group.knowledge_bases) if group.knowledge_bases else 0,
        # 返回成员 ID 列表与授权知识库 ID 列表，方便前端回显选择
        "member_ids": [m.id for m in group.members] if group.members else [],
        "kb_ids": [k.id for k in group.knowledge_bases] if group.knowledge_bases else []
    }

@router.post("", response_model=ResponseModel)
def create_user_group(
    group: UserGroupCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """创建用户组"""
    db_group = db.query(UserGroup).filter(UserGroup.name == group.name).first()
    if db_group:
        return ResponseModel(code=400, msg="用户组名称已存在")
    
    new_group = UserGroup(name=group.name, description=group.description)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return ResponseModel(data=group_to_dict(new_group))

@router.get("", response_model=ResponseModel)
def get_user_groups(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """获取所有用户组列表"""
    groups = db.query(UserGroup).all()
    return ResponseModel(data=[group_to_dict(g) for g in groups])

@router.put("/{group_id}", response_model=ResponseModel)
def update_user_group(
    group_id: int,
    group: UserGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新用户组基本信息"""
    db_group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not db_group:
        return ResponseModel(code=404, msg="用户组不存在")
    
    # 检查重名
    dup_group = db.query(UserGroup).filter(UserGroup.name == group.name, UserGroup.id != group_id).first()
    if dup_group:
        return ResponseModel(code=400, msg="用户组名称已存在")
        
    db_group.name = group.name
    db_group.description = group.description
    db.commit()
    db.refresh(db_group)
    return ResponseModel(data=group_to_dict(db_group))

@router.delete("/{group_id}", response_model=ResponseModel)
def delete_user_group(
    group_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """删除用户组，清理级联关联表数据"""
    db_group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not db_group:
        return ResponseModel(code=404, msg="用户组不存在")
    
    db.delete(db_group)
    db.commit()
    return ResponseModel(msg="用户组删除成功")

@router.post("/{group_id}/members", response_model=ResponseModel)
def add_group_members(
    group_id: int, 
    req: GroupMembersAdd, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """同步/更新用户组成员列表（覆盖式）"""
    db_group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not db_group:
        return ResponseModel(code=404, msg="用户组不存在")
    
    # 1. 物理清除当前组内所有成员关系
    db.query(UserGroupMember).filter(UserGroupMember.group_id == group_id).delete()
    
    # 2. 依次插入合法的成员 ID
    valid_users = db.query(User).filter(User.id.in_(req.user_ids)).all()
    valid_user_ids = [u.id for u in valid_users]
    
    for uid in valid_user_ids:
        db.add(UserGroupMember(user_id=uid, group_id=group_id))
        
    db.commit()
    db.refresh(db_group)
    return ResponseModel(msg="用户组成员更新成功", data=group_to_dict(db_group))

@router.post("/{group_id}/kb-access", response_model=ResponseModel)
def set_group_kb_access(
    group_id: int, 
    req: GroupKbAccess, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """授权/同步用户组的可访问知识库列表（覆盖式）"""
    db_group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not db_group:
        return ResponseModel(code=404, msg="用户组不存在")
    
    # 1. 物理清除当前组内所有知识库授权
    db.query(KbGroupAccess).filter(KbGroupAccess.group_id == group_id).delete()
    
    # 2. 依次插入合法的知识库授权映射
    valid_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(req.kb_ids)).all()
    valid_kb_ids = [k.id for k in valid_kbs]
    
    for kbid in valid_kb_ids:
        db.add(KbGroupAccess(kb_id=kbid, group_id=group_id))
        
    db.commit()
    db.refresh(db_group)
    return ResponseModel(msg="用户组知识库授权成功", data=group_to_dict(db_group))
