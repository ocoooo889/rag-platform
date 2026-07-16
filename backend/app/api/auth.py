from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schema.schemas import ResponseModel
# 导入并重新导出认证工具，保证与 V1 其它模块兼容
from app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    oauth2_scheme
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=ResponseModel)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录接口，验证用户名密码并生成 JWT 访问令牌"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        return ResponseModel(code=401, msg="用户名或密码错误")
    
    if user.status != "启用":
        return ResponseModel(code=403, msg="用户已被停用")
    
    # 签发 JWT
    access_token = create_access_token(
        data={"sub": user.username, "role_id": user.role_id}
    )
    return ResponseModel(data={"access_token": access_token, "token_type": "bearer"})
