"""RAG 评测 API — 黄金集基线跑批"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.services.rag_eval_service import run_golden_eval
from app.utils.auth import get_current_user
from app.utils.permission import require_kb_access
from app.utils.response import fail, ok

router = APIRouter(tags=["RAG评测"])


class RagEvalRunRequest(BaseModel):
    kb_id: str
    doc_id: str | None = None
    modes: list[str] = Field(default_factory=lambda: ["keyword", "vector", "hybrid"])
    top_n: int = Field(default=3, ge=1, le=10)
    save_csv: bool = True


@router.post("/eval/run")
async def rag_eval_run(
    req: RagEvalRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    对指定知识库文档跑黄金集检索评测。
    结果写入 rag-tuning/results（save_csv=true 时）并返回 JSON 明细。
    """
    kb_id = (req.kb_id or "").strip()
    if not kb_id:
        return fail(400, "缺少必填参数: kb_id")

    await require_kb_access(kb_id, current_user, db)

    try:
        data = await run_golden_eval(
            kb_id=kb_id,
            doc_id=(req.doc_id or "").strip() or None,
            modes=req.modes,
            top_n=req.top_n,
            save_csv=req.save_csv,
        )
    except ValueError as e:
        return fail(400, str(e))
    except Exception as e:  # noqa: BLE001
        return fail(5001, f"评测执行失败: {e}")

    return ok(data)
