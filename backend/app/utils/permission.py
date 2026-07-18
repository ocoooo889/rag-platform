from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, UserGroupMember, KbGroupAccess, UserKbAccess
from app.utils.auth import get_current_user
from app.utils.exceptions import BusinessException


def is_admin(user: User) -> bool:
    """判断用户是否为管理员角色（库内英文码 admin）。"""
    if not user.role:
        return False
    role_name = user.role.name if hasattr(user.role, "name") else str(user.role)
    return role_name == "admin"


def admin_denied_response():
    """非管理员时返回统一 403 业务体（供 API 层 early return）。"""
    from app.schema.response_schema import ResponseModel

    return ResponseModel(code=403, msg="权限不足，仅管理员可执行此操作")


def ensure_admin_or_response(user: User):
    """若非 admin 返回 ResponseModel，否则返回 None。"""
    if not is_admin(user):
        return admin_denied_response()
    return None


async def get_user_accessible_kb_ids(db: Session, user_id: int) -> list[str]:
    """获取非 admin 用户可访问知识库：用户组授权 ∪ 用户直接授权。"""
    group_memberships = (
        db.query(UserGroupMember.group_id)
        .filter(UserGroupMember.user_id == user_id)
        .all()
    )
    group_ids = [m[0] for m in group_memberships]

    kb_ids: set[str] = set()

    if group_ids:
        kb_accesses = (
            db.query(KbGroupAccess.kb_id)
            .filter(KbGroupAccess.group_id.in_(group_ids))
            .all()
        )
        kb_ids.update(k[0] for k in kb_accesses)

    direct = (
        db.query(UserKbAccess.kb_id)
        .filter(UserKbAccess.user_id == user_id)
        .all()
    )
    kb_ids.update(k[0] for k in direct)

    return list(kb_ids)


async def require_kb_access(
    kb_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """知识库访问权限校验。admin 放行；否则校验用户组+直接授权，无权抛业务 403。"""
    if is_admin(user):
        return

    accessible_ids = await get_user_accessible_kb_ids(db, user.id)
    if kb_id not in accessible_ids:
        raise BusinessException(
            code=403, msg="您无权访问该知识库", http_status=403
        )
