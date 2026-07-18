"""角色 code → 展示名，供登录 /me 等统一用户载荷。"""

from __future__ import annotations

from typing import Any

from app.db.models import User

_ROLE_LABELS = {
    "admin": "管理员",
    "user": "普通用户",
}


def role_code_of(user: User) -> str:
    if user.role and getattr(user.role, "name", None):
        return str(user.role.name)
    return "user"


def role_label_of(code: str) -> str:
    return _ROLE_LABELS.get(code, code or "未知")


def build_user_payload(user: User) -> dict[str, Any]:
    role_code = role_code_of(user)
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": getattr(user, "avatar_url", None) or "",
        "role": role_code,
        "role_name": role_label_of(role_code),
        "status": user.status,
    }
