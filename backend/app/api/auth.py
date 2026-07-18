from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.db.models import User
from app.schema.response_schema import ResponseModel
from app.utils.auth import (
    verify_password,
    create_access_token,
    get_current_user,
)
from app.utils.role_labels import build_user_payload

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
