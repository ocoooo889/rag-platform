
from pydantic import BaseModel, ConfigDict

from pydantic import BaseModel

from typing import Optional, List

# 角色相关
class RoleBase(BaseModel):
    name: str
    permissions: List[str] = []

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    pass

# 用户组相关
class UserGroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class UserGroupCreate(UserGroupBase):
    pass

class UserGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

# 用户组成员管理
class GroupMembersAdd(BaseModel):
    user_ids: List[int]

# 用户组知识库授权
class GroupKbAccess(BaseModel):
    kb_ids: List[str]

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

# 知识库相关
class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    group_ids: Optional[List[int]] = [] # V2 创建知识库时可以指定授权的用户组

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

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


