from pydantic import BaseModel, Field


class HitTestRequest(BaseModel):
    kb_id: str
    # 单文档（契约主字段）；与 doc_ids 同时传入时合并去重
    doc_id: str | None = None
    # 多文档扩展：一次检索多篇，结果按 score 合并截断 top_n
    doc_ids: list[str] | None = None
    search_type: str
    query: str
    top_n: int = Field(default=3, ge=1, le=10)


class ChatRequest(BaseModel):
    kb_id: str
    query: str
    session_id: str | None = None
    search_type: str = "hybrid"
    top_n: int = Field(default=3, ge=1, le=10)


class ChatSessionUpdate(BaseModel):
    """会话管理：重命名 / 置顶"""
    title: str | None = Field(default=None, max_length=25)
    pinned: bool | None = None
