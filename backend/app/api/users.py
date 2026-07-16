from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import User, Role, UserGroupMember, UserGroup
from app.schema.request_schema import UserCreate, UserUpdate
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user, get_password_hash

router = APIRouter(prefix="/api/users", tags=["users"])

def user_to_dict(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "status": user.status,
        "role_id": user.role_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "groups": [
            {"id": g.id, "name": g.name, "description": g.description} for g in user.groups
        ] if user.groups else []
    }

@router.post("", response_model=ResponseModel)
def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """创建新用户"""
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        return ResponseModel(code=400, msg="用户名已存在")
    
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if not role:
            return ResponseModel(code=400, msg="指定的角色不存在")

    hashed_pw = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        hashed_password=hashed_pw,
        display_name=user.display_name,
        status=user.status,
        role_id=user.role_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return ResponseModel(data=user_to_dict(new_user))

@router.get("", response_model=ResponseModel)
def get_users(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """获取系统所有用户列表"""
    users = db.query(User).all()
    return ResponseModel(data=[user_to_dict(u) for u in users])

@router.put("/{user_id}", response_model=ResponseModel)
def update_user(
    user_id: int, 
    user: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """更新用户信息，支持角色和关联用户组的更新"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return ResponseModel(code=404, msg="用户不存在")
    
    if user.role_id is not None:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if not role:
            return ResponseModel(code=400, msg="指定的角色不存在")
        db_user.role_id = user.role_id

    if user.display_name is not None:
        db_user.display_name = user.display_name
    
    if user.status is not None:
        db_user.status = user.status

    # 处理所属用户组的关联更新
    if user.group_ids is not None:
        # 验证组的合法性
        valid_groups = db.query(UserGroup).filter(UserGroup.id.in_(user.group_ids)).all()
        valid_group_ids = [g.id for g in valid_groups]
        
        # 清除原有用户组绑定
        db.query(UserGroupMember).filter(UserGroupMember.user_id == user_id).delete()
        
        # 写入新的组绑定
        for gid in valid_group_ids:
            db.add(UserGroupMember(user_id=user_id, group_id=gid))

    db.commit()
    db.refresh(db_user)
    return ResponseModel(data=user_to_dict(db_user))

@router.delete("/{user_id}", response_model=ResponseModel)
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """逻辑删除用户：修改状态为 '已停用'"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return ResponseModel(code=404, msg="用户不存在")
    
    db_user.status = "已停用"
    db.commit()
    return ResponseModel(msg="用户删除(停用)成功")
