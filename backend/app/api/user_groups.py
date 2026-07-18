from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, UserGroup, UserGroupMember, KbGroupAccess, KnowledgeBase
from app.schema.request_schema import UserGroupCreate, GroupMembersAdd, GroupKbAccess
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user
from app.utils.permission import ensure_admin_or_response

router = APIRouter(prefix="/api/user-groups", tags=["user-groups"])


def group_to_dict(group: UserGroup):
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "member_count": len(group.members) if group.members else 0,
        "kb_count": len(group.knowledge_bases) if group.knowledge_bases else 0,
        "member_ids": [m.id for m in group.members] if group.members else [],
        "kb_ids": [k.id for k in group.knowledge_bases] if group.knowledge_bases else [],
    }


@router.post("", response_model=ResponseModel)
def create_user_group(
    group: UserGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

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
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    groups = db.query(UserGroup).all()
    return ResponseModel(data=[group_to_dict(g) for g in groups])


@router.put("/{group_id}", response_model=ResponseModel)
def update_user_group(
    group_id: int,
    group: UserGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not db_group:
        return ResponseModel(code=404, msg="用户组不存在")

    dup_group = (
        db.query(UserGroup)
        .filter(UserGroup.name == group.name, UserGroup.id != group_id)
        .first()
    )
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
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

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
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not db_group:
        return ResponseModel(code=404, msg="用户组不存在")

    db.query(UserGroupMember).filter(UserGroupMember.group_id == group_id).delete()
    valid_users = db.query(User).filter(User.id.in_(req.user_ids)).all()
    for uid in [u.id for u in valid_users]:
        db.add(UserGroupMember(user_id=uid, group_id=group_id))

    db.commit()
    db.refresh(db_group)
    return ResponseModel(msg="用户组成员更新成功", data=group_to_dict(db_group))


@router.post("/{group_id}/kb-access", response_model=ResponseModel)
def set_group_kb_access(
    group_id: int,
    req: GroupKbAccess,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not db_group:
        return ResponseModel(code=404, msg="用户组不存在")

    db.query(KbGroupAccess).filter(KbGroupAccess.group_id == group_id).delete()
    valid_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(req.kb_ids)).all()
    for kbid in [k.id for k in valid_kbs]:
        db.add(KbGroupAccess(kb_id=kbid, group_id=group_id))

    db.commit()
    db.refresh(db_group)
    return ResponseModel(msg="用户组知识库授权成功", data=group_to_dict(db_group))
