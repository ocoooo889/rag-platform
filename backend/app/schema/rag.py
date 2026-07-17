from pydantic import BaseModel, Field


class HitTestRequest(BaseModel):
    kb_id: str
    doc_id: str
    search_type: str
    query: str
    top_n: int = Field(default=3, ge=1, le=10)


class ChatRequest(BaseModel):
    kb_id: str
    query: str
    session_id: str | None = None
    search_type: str = "hybrid"
    top_n: int = Field(default=3, ge=1, le=10)
