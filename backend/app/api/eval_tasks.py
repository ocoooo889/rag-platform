"""
评测任务 API — 对齐前端 frontend/src/api/eval.ts

路由：
  GET/POST  /api/eval/tasks
  DELETE    /api/eval/tasks/{id}
  POST      /api/eval/tasks/{id}/run
  GET       /api/eval/tasks/{id}/progress
  GET/POST  /api/eval/tasks/{id}/samples
  POST      /api/eval/tasks/{id}/samples/import
  GET       /api/eval/tasks/{id}/results
  GET       /api/eval/compare?ids=
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.db.sqlite_helper import kb_exists
from app.services import eval_task_store
from app.utils.auth import get_current_user
from app.utils.permission import require_kb_access
from app.utils.response import fail, ok

router = APIRouter(prefix="/api/eval", tags=["评测任务"])


class EvalRunParams(BaseModel):
    kb_id: str | int
    kb_name: str | None = None
    embedding_model: str = "text-embedding-v4"
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunk_mode: str | None = "recursive"
    separators: str | None = None
    clean_enabled: bool | None = True


class EvalTaskCreateRequest(BaseModel):
    name: str
    rule_json: str | None = None
    params: EvalRunParams


class EvalSampleCreateRequest(BaseModel):
    question: str
    expected_answer: str
    tags: str | None = None


async def _ensure_task_access(
    task_id: str, user: User, db: Session
) -> dict[str, Any] | None:
    task = await eval_task_store.get_task(task_id)
    if not task:
        return None
    kb_id = str((task.get("params") or {}).get("kb_id") or "").strip()
    if kb_id:
        await require_kb_access(kb_id, user, db)
    return task


@router.get("/tasks")
async def list_eval_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """评测任务分页列表。"""
    _ = current_user, db
    data = await eval_task_store.list_tasks(
        page=page,
        page_size=page_size,
        status=(status or "").strip() or None,
        keyword=(keyword or "").strip() or None,
    )
    return ok(data)


@router.post("/tasks")
async def create_eval_task(
    req: EvalTaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建评测任务（pending，不自动跑）。"""
    name = (req.name or "").strip()
    if not name:
        return fail(400, "请填写任务名称")
    params = req.params.model_dump()
    kb_id = str(params.get("kb_id") or "").strip()
    if not kb_id:
        return fail(400, "请选择知识库")
    if not kb_exists(kb_id):
        return fail(404, "知识库不存在")
    await require_kb_access(kb_id, current_user, db)

    task = await eval_task_store.create_task(
        name=name,
        params=params,
        rule_json=req.rule_json,
        user_id=str(getattr(current_user, "id", "") or ""),
    )
    return ok(task)


@router.delete("/tasks/{task_id}")
async def delete_eval_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除评测任务（运行中会取消）。"""
    task = await _ensure_task_access(task_id, current_user, db)
    if not task:
        return fail(404, "任务不存在")
    ok_del, msg = await eval_task_store.delete_task(task_id)
    if not ok_del:
        return fail(404, msg)
    return ok({"id": task_id, "deleted": True, "message": msg})


@router.post("/tasks/{task_id}/run")
async def run_eval_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """启动评测，返回进度快照。"""
    task = await _ensure_task_access(task_id, current_user, db)
    if not task:
        return fail(404, "任务不存在")
    try:
        progress = await eval_task_store.start_run(task_id)
    except KeyError:
        return fail(404, "任务不存在")
    except ValueError as e:
        return fail(400, str(e))
    except Exception as e:  # noqa: BLE001
        return fail(5001, f"启动评测失败: {e}")
    return ok(progress)


@router.get("/tasks/{task_id}/progress")
async def get_eval_progress(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询评测进度。"""
    task = await _ensure_task_access(task_id, current_user, db)
    if not task:
        return fail(404, "任务不存在")
    try:
        progress = await eval_task_store.get_progress(task_id)
    except KeyError:
        return fail(404, "任务不存在")
    return ok(progress)


@router.get("/tasks/{task_id}/samples")
async def list_eval_samples(
    task_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    keyword: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """样本分页列表。"""
    task = await _ensure_task_access(task_id, current_user, db)
    if not task:
        return fail(404, "任务不存在")
    try:
        data = await eval_task_store.list_samples(
            task_id,
            page=page,
            page_size=page_size,
            keyword=(keyword or "").strip() or None,
        )
    except KeyError:
        return fail(404, "任务不存在")
    return ok(data)


@router.post("/tasks/{task_id}/samples")
async def add_eval_sample(
    task_id: str,
    req: EvalSampleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动添加一条样本。"""
    task = await _ensure_task_access(task_id, current_user, db)
    if not task:
        return fail(404, "任务不存在")
    try:
        sample = await eval_task_store.add_sample(
            task_id,
            question=req.question,
            expected_answer=req.expected_answer,
            tags=req.tags,
        )
    except KeyError:
        return fail(404, "任务不存在")
    except ValueError as e:
        return fail(400, str(e))
    return ok(sample)


@router.post("/tasks/{task_id}/samples/import")
async def import_eval_samples(
    task_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传 CSV/JSON 导入样本。"""
    task = await _ensure_task_access(task_id, current_user, db)
    if not task:
        return fail(404, "任务不存在")
    content = await file.read()
    if not content:
        return fail(400, "文件为空")
    try:
        imported = await eval_task_store.import_samples(
            task_id,
            content=content,
            filename=file.filename or "samples.csv",
        )
    except KeyError:
        return fail(404, "任务不存在")
    except ValueError as e:
        return fail(400, str(e))
    except Exception as e:  # noqa: BLE001
        return fail(5001, f"导入失败: {e}")
    return ok({"imported": imported})


@router.get("/tasks/{task_id}/results")
async def get_eval_results(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """评测结果明细（数组，前端 unwrapEvalResults 兼容）。"""
    task = await _ensure_task_access(task_id, current_user, db)
    if not task:
        return fail(404, "任务不存在")
    try:
        rows = await eval_task_store.get_results(task_id)
    except KeyError:
        return fail(404, "任务不存在")
    return ok(rows)


@router.get("/compare")
async def compare_eval_tasks(
    ids: str = Query(..., description="逗号分隔的 task_id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """多任务指标对比。"""
    _ = current_user, db
    task_ids = [x.strip() for x in (ids or "").split(",") if x.strip()]
    if not task_ids:
        return fail(400, "缺少 ids")
    points = await eval_task_store.compare_tasks(task_ids)
    return ok(points)
