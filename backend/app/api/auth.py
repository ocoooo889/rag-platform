from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schema.response_schema import ResponseModel
# 导入并重新导出认证工具，保证与 V1 其它模块兼容
from app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    oauth2_scheme
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login/json", response_model=ResponseModel)
def login_json(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录接口，支持 JSON 格式，验证用户名密码并生成 JWT"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        return ResponseModel(code=401, msg="用户名或密码错误")
    
    if user.status != "启用":
        return ResponseModel(code=403, msg="用户已被停用")
    
    access_token = create_access_token(
        data={"sub": user.username, "role_id": user.role_id}
    )
    return ResponseModel(data={"access_token": access_token, "token_type": "bearer"})

@router.post("/login")
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 兼容的表单登录，专供 Swagger UI 使用"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        return {"error": "invalid_grant"}
    if user.status != "启用":
        return {"error": "user_disabled"}
    access_token = create_access_token(
        data={"sub": user.username, "role_id": user.role_id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

