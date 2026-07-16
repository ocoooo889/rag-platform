from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, UserGroupMember, KbGroupAccess
from app.utils.auth import get_current_user

def is_admin(user: User) -> bool:
    """判断用户是否为管理员角色"""
    if not user.role:
        return False
    # 支持 role 关联对象或直接是字符串 role
    role_name = user.role.name if hasattr(user.role, "name") else str(user.role)
    return role_name == "admin"

async def get_user_accessible_kb_ids(db: Session, user_id: int) -> list[int]:
    """获取非 admin 用户所属用户组被授权的知识库 ID 列表"""
    # 1. 查询用户所属的所有用户组 ID
    group_memberships = db.query(UserGroupMember.group_id)\
        .filter(UserGroupMember.user_id == user_id).all()
    group_ids = [m[0] for m in group_memberships]

    if not group_ids:
        return []  # 未分配用户组，无权限访问任何知识库

    # 2. 查询这些用户组被授权的知识库 ID
    kb_accesses = db.query(KbGroupAccess.kb_id)\
        .filter(KbGroupAccess.group_id.in_(group_ids)).all()
    return list(set(k[0] for k in kb_accesses))

async def require_kb_access(kb_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """知识库访问权限校验依赖项。
    如果是 admin 角色，放行；
    如果是非 admin 角色，校验当前用户是否被授权该知识库访问权，无权则抛出 403 异常。
    """
    if is_admin(user):
        return  # 管理员放行

    accessible_ids = await get_user_accessible_kb_ids(db, user.id)
    if kb_id not in accessible_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问该知识库"
        )
