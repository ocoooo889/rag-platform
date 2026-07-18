from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

# 统一响应模型
class ResponseModel(BaseModel):
    code: int = 0
    msg: str = "success"
    data: Any = None

# 角色相关
class RoleBase(BaseModel):
    name: str
    permissions: List[str] = []

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    pass

class RoleOut(RoleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# 用户组相关
class UserGroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class UserGroupCreate(UserGroupBase):
    pass

class UserGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class UserGroupOut(UserGroupBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# 用户相关
class UserBase(BaseModel):
    username: str
    display_name: str
    status: str = "启用"
    role_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None
    role_id: Optional[int] = None
    group_ids: Optional[List[int]] = None # V2 支持更新所属用户组

class UserOut(UserBase):
    id: int
    created_at: Optional[datetime] = None
    groups: List[UserGroupOut] = [] # V2 新增：所属用户组
    model_config = ConfigDict(from_attributes=True)

# Token 认证相关
class Token(BaseModel):
    access_token: str
    token_type: str

# 知识库相关
class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    group_ids: Optional[List[int]] = [] # V2 创建知识库时可以指定授权的用户组

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class KnowledgeBaseOut(KnowledgeBaseBase):
    id: str
    created_at: Optional[datetime] = None
    document_count: int = 0
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

# 用户组成员管理
class GroupMembersAdd(BaseModel):
    user_ids: List[int]

# 用户组知识库授权（知识库为字符串 ID）
class GroupKbAccess(BaseModel):
    kb_ids: List[str]

# 大模型配置相关
class LLMConfigBase(BaseModel):
    model_type: str
    model_name: str
    api_base_url: str
    dimension: Optional[int] = None
    is_active: bool = True
    model_config = ConfigDict(protected_namespaces=())

class LLMConfigCreate(LLMConfigBase):
    pass

class LLMConfigUpdate(BaseModel):
    model_type: Optional[str] = None
    model_name: Optional[str] = None
    api_base_url: Optional[str] = None
    dimension: Optional[int] = None
    is_active: Optional[bool] = None
    model_config = ConfigDict(protected_namespaces=())

# 系统品牌白标配置
class BrandingConfigOut(BaseModel):
    brand_name: str
    brand_logo_url: str
    brand_favicon_url: str
    brand_theme_color: str
    brand_login_title: str
    brand_footer_text: str
    brand_logo_history: List[str] = []
