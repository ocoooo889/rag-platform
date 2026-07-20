from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    permissions = Column(JSON)  # 例如: ["kb:create", "doc:upload", "rag:test", "chat:send"]
    
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    display_name = Column(String)
    avatar_url = Column(String, nullable=True)  # 用户自定义头像
    role_id = Column(Integer, ForeignKey("roles.id"))
    status = Column(String, default="启用") # 启用 / 已停用
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    role = relationship("Role", back_populates="users")
    # 多对多关联：用户所属的用户组
    groups = relationship("UserGroup", secondary="user_group_members", back_populates="members")

class UserGroup(Base):
    __tablename__ = "user_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    members = relationship("User", secondary="user_group_members", back_populates="groups")
    knowledge_bases = relationship("KnowledgeBase", secondary="kb_group_access", back_populates="groups")

class UserGroupMember(Base):
    __tablename__ = "user_group_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    # 授权可访问该知识库的用户组
    groups = relationship("UserGroup", secondary="kb_group_access", back_populates="knowledge_bases")

class KbGroupAccess(Base):
    __tablename__ = "kb_group_access"
    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(String(50), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint("kb_id", "group_id", name="uq_kb_group"),)

class UserKbAccess(Base):
    """用户直接授权可访问的知识库（与用户组授权并存）"""
    __tablename__ = "user_kb_access"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kb_id = Column(String(50), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "kb_id", name="uq_user_kb"),)

class Document(Base):
    __tablename__ = "documents"
    id = Column(String(50), primary_key=True, index=True)
    kb_id = Column(String(50), ForeignKey("knowledge_bases.id", ondelete="CASCADE"))
    filename = Column(String)
    file_type = Column(String) # md / txt
    file_size = Column(Integer)
    status = Column(String, default="pending") # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    # 切分策略（上传可选；默认 recursive）
    split_strategy = Column(String(50), nullable=True, default="recursive")
    chunk_size = Column(Integer, nullable=True)
    chunk_overlap = Column(Integer, nullable=True)
    split_meta = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    """分片元数据（与契约 / ingest 字段对齐）"""
    __tablename__ = "chunks"
    id = Column(String(50), primary_key=True, index=True)
    doc_id = Column(String(50), ForeignKey("documents.id", ondelete="CASCADE"))
    kb_id = Column(String(50), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    chroma_id = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    """对话历史（3号 chat 写入）"""
    __tablename__ = "conversations"
    id = Column(String(50), primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    kb_id = Column(String(50), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    references_json = Column("references", Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMConfig(Base):
    __tablename__ = "model_configs"
    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String) # llm / embedding
    model_name = Column(String)
    api_base_url = Column(String)
    dimension = Column(Integer, nullable=True) # 仅 embedding 有值 (如 1536)
    is_active = Column(Boolean, default=True)

class SystemConfig(Base):
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, index=True, nullable=False)
    config_value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
