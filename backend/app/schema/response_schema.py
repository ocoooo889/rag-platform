from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

from .request_schema import RoleBase, UserGroupBase, UserBase, KnowledgeBaseBase

# 统一响应模型
class ResponseModel(BaseModel):
    code: int = 0
    msg: str = "success"
    data: Any = None

class RoleOut(RoleBase):
    id: int
    class Config:
        from_attributes = True
        orm_mode = True

class UserGroupOut(UserGroupBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
        orm_mode = True

class UserOut(UserBase):
    id: int
    created_at: Optional[datetime] = None
    groups: List[UserGroupOut] = [] # V2 新增：所属用户组
    class Config:
        from_attributes = True
        orm_mode = True

# Token 认证相关
class Token(BaseModel):
    access_token: str
    token_type: str

class KnowledgeBaseOut(KnowledgeBaseBase):
    id: str
    created_at: Optional[datetime] = None
    document_count: int = 0
    class Config:
        from_attributes = True
        orm_mode = True

# 文档相关
class DocumentOut(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
        orm_mode = True

# 系统品牌白标配置
class BrandingConfigOut(BaseModel):
    brand_name: str
    brand_logo_url: str
    brand_favicon_url: str
    brand_theme_color: str
    brand_login_title: str
    brand_footer_text: str
