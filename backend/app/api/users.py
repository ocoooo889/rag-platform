from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, Role, UserGroupMember, UserGroup, KnowledgeBase, UserKbAccess
from app.schema.request_schema import UserCreate, UserUpdate
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user, get_password_hash
from app.utils.permission import ensure_admin_or_response

router = APIRouter(prefix="/api/users", tags=["users"])


def _user_kb_ids(db: Session, user_id: int) -> list[str]:
    rows = db.query(UserKbAccess.kb_id).filter(UserKbAccess.user_id == user_id).all()
    return [r[0] for r in rows]


def _replace_user_kb_access(db: Session, user_id: int, kb_ids):
    """全量覆盖用户直接知识库授权；kb_ids 为空列表则清空。"""
    if kb_ids is None:
        return
    valid = (
        db.query(KnowledgeBase.id)
        .filter(KnowledgeBase.id.in_(kb_ids))
        .all()
        if kb_ids
        else []
    )
    valid_ids = [r[0] for r in valid]
    db.query(UserKbAccess).filter(UserKbAccess.user_id == user_id).delete()
    for kid in valid_ids:
        db.add(UserKbAccess(user_id=user_id, kb_id=kid))


def user_to_dict(user: User, db: Session):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": getattr(user, "avatar_url", None) or "",
        "status": user.status,
        "role_id": user.role_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "groups": [
            {"id": g.id, "name": g.name, "description": g.description}
            for g in user.groups
        ]
        if user.groups
        else [],
        "kb_ids": _user_kb_ids(db, user.id),
    }


@router.post("", response_model=ResponseModel)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

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
        role_id=user.role_id,
    )
    db.add(new_user)
    db.flush()
    _replace_user_kb_access(db, new_user.id, user.kb_ids if user.kb_ids is not None else [])
    db.commit()
    db.refresh(new_user)
    return ResponseModel(data=user_to_dict(new_user, db))


@router.get("", response_model=ResponseModel)
def get_users(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    users = db.query(User).all()
    return ResponseModel(data=[user_to_dict(u, db) for u in users])


@router.put("/{user_id}", response_model=ResponseModel)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

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

    if user.group_ids is not None:
        valid_groups = db.query(UserGroup).filter(UserGroup.id.in_(user.group_ids)).all()
        valid_group_ids = [g.id for g in valid_groups]
        db.query(UserGroupMember).filter(UserGroupMember.user_id == user_id).delete()
        for gid in valid_group_ids:
            db.add(UserGroupMember(user_id=user_id, group_id=gid))

    if user.kb_ids is not None:
        _replace_user_kb_access(db, user_id, user.kb_ids)

    db.commit()
    db.refresh(db_user)
    return ResponseModel(data=user_to_dict(db_user, db))


@router.delete("/{user_id}", response_model=ResponseModel)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return ResponseModel(code=404, msg="用户不存在")

    db_user.status = "已停用"
    db.commit()
    return ResponseModel(msg="用户删除(停用)成功")
