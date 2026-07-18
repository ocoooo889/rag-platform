from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
import os
import shutil
import time

from app.db.database import get_db
from app.db.models import User
from app.schema.response_schema import ResponseModel
from app.utils.auth import (
    verify_password,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from app.utils.role_labels import build_user_payload

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATAR_DIR = "./uploads/avatars"


class LoginRequest(BaseModel):
    username: str
    password: str


def _load_user_by_username(db: Session, username: str) -> Optional[User]:
    return (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.username == username)
        .first()
    )


def _login_success_data(user: User) -> dict:
    access_token = create_access_token(
        data={"sub": user.username, "role_id": user.role_id}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": build_user_payload(user),
    }


@router.post("/login/json", response_model=ResponseModel)
def login_json(req: LoginRequest, db: Session = Depends(get_db)):
    """JSON 登录（与 form 口同构 data）。"""
    user = _load_user_by_username(db, req.username)
    if not user or not verify_password(req.password, user.hashed_password):
        return ResponseModel(code=401, msg="用户名或密码错误")
    if user.status != "启用":
        return ResponseModel(code=403, msg="用户已被停用")
    return ResponseModel(data=_login_success_data(user))


@router.post("/login")
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """表单登录（前端现网主路径），统一 {code,msg,data}。"""
    user = _load_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        return {"code": 401, "msg": "用户名或密码错误", "data": None}
    if user.status != "启用":
        return {"code": 403, "msg": "用户已被停用", "data": None}
    return {"code": 0, "msg": "success", "data": _login_success_data(user)}


@router.get("/me", response_model=ResponseModel)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return ResponseModel(data=build_user_payload(current_user))


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None


@router.put("/profile", response_model=ResponseModel)
def update_profile(
    req: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户修改个人信息（显示名 / 密码）。"""
    if req.display_name is not None:
        name = req.display_name.strip()
        if not name:
            return ResponseModel(code=400, msg="显示名不能为空")
        if len(name) > 32:
            return ResponseModel(code=400, msg="显示名不能超过 32 个字")
        current_user.display_name = name

    if req.new_password:
        if not req.old_password:
            return ResponseModel(code=400, msg="请输入当前密码")
        if not verify_password(req.old_password, current_user.hashed_password):
            return ResponseModel(code=400, msg="当前密码不正确")
        if len(req.new_password) < 6:
            return ResponseModel(code=400, msg="新密码至少 6 位")
        current_user.hashed_password = get_password_hash(req.new_password)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return ResponseModel(data=build_user_payload(current_user), msg="资料已更新")


@router.post("/avatar", response_model=ResponseModel)
def upload_avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户上传自定义头像（正方形图，png/jpg/webp）。"""
    if not avatar or not avatar.filename:
        return ResponseModel(code=400, msg="请选择头像文件")

    ext = os.path.splitext(avatar.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        return ResponseModel(code=400, msg="仅支持 png / jpg / webp")

    os.makedirs(AVATAR_DIR, exist_ok=True)
    ts = int(time.time() * 1000)
    filename = f"u{current_user.id}_{ts}.png"
    path = os.path.join(AVATAR_DIR, filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(avatar.file, buffer)

    # 清理该用户旧头像文件（保留最新）
    prefix = f"u{current_user.id}_"
    for name in os.listdir(AVATAR_DIR):
        if name.startswith(prefix) and name != filename:
            try:
                os.remove(os.path.join(AVATAR_DIR, name))
            except OSError:
                pass

    url = f"/uploads/avatars/{filename}?v={ts}"
    current_user.avatar_url = url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return ResponseModel(data=build_user_payload(current_user), msg="头像已更新")
