"""
评测任务内存存储 — 对齐前端 eval.ts / types（EvalTask、Sample、Progress、Results）。

流程：创建(pending) → 导入/添加样本 → POST run → 轮询 progress → GET results
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.services.rag_eval_service import _retrieve_for_eval, resolve_kb_doc
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

_TASKS: dict[str, dict[str, Any]] = {}
_SAMPLES: dict[str, list[dict[str, Any]]] = {}  # task_id -> samples
_RESULTS: dict[str, list[dict[str, Any]]] = {}  # task_id -> metric rows
_RUNNERS: dict[str, asyncio.Task] = {}
_LOCK = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _public_task(task: dict[str, Any]) -> dict[str, Any]:
    """前端 EvalTask 字段。"""
    return {
        "id": task["id"],
        "name": task.get("name") or "",
        "status": task.get("status") or "pending",
        "created_at": task.get("created_at") or _now(),
        "sample_count": int(task.get("sample_count") or 0),
        "rule_json": task.get("rule_json"),
        "error_message": task.get("error_message"),
        "params": task.get("params") or {},
        "progress": int(task.get("progress") or 0),
        "progress_message": task.get("progress_message"),
    }


def _progress_view(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["id"],
        "status": task.get("status") or "pending",
        "progress": int(task.get("progress") or 0),
        "message": task.get("progress_message") or "",
    }


def _kb_id_from_params(params: dict[str, Any] | None) -> str:
    if not params:
        return ""
    raw = params.get("kb_id")
    if raw is None:
        return ""
    return str(raw).strip()


async def create_task(
    *,
    name: str,
    params: dict[str, Any],
    rule_json: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """仅创建任务（pending），不自动跑。"""
    task_id = new_id("eval_")
    task: dict[str, Any] = {
        "id": task_id,
        "name": (name or "").strip() or f"评测任务-{task_id}",
        "status": "pending",
        "created_at": _now(),
        "sample_count": 0,
        "rule_json": rule_json,
        "error_message": None,
        "params": dict(params or {}),
        "progress": 0,
        "progress_message": "待上传样本后启动",
        "created_by": user_id,
        "_cancel": False,
    }
    async with _LOCK:
        _TASKS[task_id] = task
        _SAMPLES[task_id] = []
        _RESULTS[task_id] = []
    return _public_task(task)


async def get_task(task_id: str) -> dict[str, Any] | None:
    async with _LOCK:
        task = _TASKS.get(task_id)
        return _public_task(task) if task else None


async def get_task_raw(task_id: str) -> dict[str, Any] | None:
    async with _LOCK:
        task = _TASKS.get(task_id)
        return deepcopy(task) if task else None


async def list_tasks(
    *,
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    keyword: str | None = None,
) -> dict[str, Any]:
    async with _LOCK:
        items = list(_TASKS.values())
    if status:
        items = [t for t in items if t.get("status") == status]
    if keyword:
        kw = keyword.strip().lower()
        items = [t for t in items if kw in str(t.get("name") or "").lower()]
    items.sort(key=lambda t: t.get("created_at") or "", reverse=True)
    total = len(items)
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 10), 200))
    start = (page - 1) * page_size
    slice_items = items[start : start + page_size]
    return {
        "items": [_public_task(t) for t in slice_items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def delete_task(task_id: str) -> tuple[bool, str]:
    async with _LOCK:
        task = _TASKS.get(task_id)
        if not task:
            return False, "任务不存在"
        task["_cancel"] = True
        runner = _RUNNERS.get(task_id)

    if runner and not runner.done():
        runner.cancel()
        try:
            await runner
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            pass

    async with _LOCK:
        _RUNNERS.pop(task_id, None)
        existed = _TASKS.pop(task_id, None) is not None
        _SAMPLES.pop(task_id, None)
        _RESULTS.pop(task_id, None)
    if not existed:
        return False, "任务不存在"
    return True, "已删除"


async def add_sample(
    task_id: str,
    *,
    question: str,
    expected_answer: str,
    tags: str | None = None,
) -> dict[str, Any]:
    q = (question or "").strip()
    a = (expected_answer or "").strip()
    if not q or not a:
        raise ValueError("question 与 expected_answer 不能为空")
    async with _LOCK:
        task = _TASKS.get(task_id)
        if not task:
            raise KeyError("任务不存在")
        if task.get("status") == "running":
            raise ValueError("任务运行中，无法添加样本")
        sample = {
            "id": new_id("s_"),
            "task_id": task_id,
            "question": q,
            "expected_answer": a,
            "tags": (tags or "").strip() or None,
        }
        _SAMPLES.setdefault(task_id, []).append(sample)
        task["sample_count"] = len(_SAMPLES[task_id])
        if task.get("status") == "completed":
            task["status"] = "pending"
            task["progress"] = 0
            task["progress_message"] = "样本已更新，请重新运行"
            _RESULTS[task_id] = []
        return deepcopy(sample)


async def list_samples(
    task_id: str,
    *,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
) -> dict[str, Any]:
    async with _LOCK:
        if task_id not in _TASKS:
            raise KeyError("任务不存在")
        items = list(_SAMPLES.get(task_id) or [])
    if keyword:
        kw = keyword.strip().lower()
        items = [
            s
            for s in items
            if kw in str(s.get("question") or "").lower()
            or kw in str(s.get("expected_answer") or "").lower()
        ]
    total = len(items)
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 10), 200))
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _parse_import_text(raw: str, filename: str) -> list[dict[str, str]]:
    """解析 CSV / JSON / JSONL 样本文件。"""
    text = (raw or "").strip()
    if not text:
        return []
    name = (filename or "").lower()
    rows: list[dict[str, str]] = []

    if name.endswith(".json"):
        data = json.loads(text)
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        if not isinstance(data, list):
            raise ValueError("JSON 须为样本数组")
        for item in data:
            if not isinstance(item, dict):
                continue
            q = str(item.get("question") or item.get("query") or "").strip()
            a = str(
                item.get("expected_answer")
                or item.get("answer")
                or item.get("expected")
                or ""
            ).strip()
            if q and a:
                rows.append(
                    {
                        "question": q,
                        "expected_answer": a,
                        "tags": str(item.get("tags") or "").strip(),
                    }
                )
        return rows

    # 默认按 CSV（含 .csv / .txt）
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        # 无表头：question,expected_answer[,tags]
        plain = csv.reader(io.StringIO(text))
        for parts in plain:
            if len(parts) < 2:
                continue
            q, a = parts[0].strip(), parts[1].strip()
            tags = parts[2].strip() if len(parts) > 2 else ""
            if q and a:
                rows.append({"question": q, "expected_answer": a, "tags": tags})
        return rows

    # 表头别名
    def _pick(row: dict, *keys: str) -> str:
        lower = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
        for key in keys:
            if key in lower and lower[key] is not None:
                return str(lower[key]).strip()
        return ""

    for row in reader:
        q = _pick(row, "question", "query", "q", "问题")
        a = _pick(row, "expected_answer", "answer", "expected", "期望答案", "参考答案")
        tags = _pick(row, "tags", "tag", "标签")
        if q and a:
            rows.append({"question": q, "expected_answer": a, "tags": tags})
    return rows


async def import_samples(task_id: str, *, content: bytes, filename: str) -> int:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="ignore")
    parsed = _parse_import_text(text, filename)
    if not parsed:
        raise ValueError("未解析到有效样本（需含 question / expected_answer）")
    n = 0
    for row in parsed:
        await add_sample(
            task_id,
            question=row["question"],
            expected_answer=row["expected_answer"],
            tags=row.get("tags") or None,
        )
        n += 1
    return n


def _token_set(text: str) -> set[str]:
    parts = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", (text or "").lower())
    return {p for p in parts if p}


def _overlap_score(expected: str, actual: str) -> float:
    e = _token_set(expected)
    a = _token_set(actual)
    if not e:
        return 0.0
    if not a:
        return 0.0
    inter = len(e & a)
    precision = inter / max(len(a), 1)
    recall = inter / max(len(e), 1)
    if precision + recall <= 0:
        return 0.0
    f1 = 2 * precision * recall / (precision + recall)
    return round(f1, 4)


async def start_run(task_id: str) -> dict[str, Any]:
    """启动异步评测，立即返回 progress。"""
    async with _LOCK:
        task = _TASKS.get(task_id)
        if not task:
            raise KeyError("任务不存在")
        if task.get("status") == "running":
            return _progress_view(task)
        samples = list(_SAMPLES.get(task_id) or [])
        if not samples:
            raise ValueError("请先导入或添加评测样本")
        kb_id = _kb_id_from_params(task.get("params"))
        if not kb_id:
            raise ValueError("任务缺少 params.kb_id")
        task["_cancel"] = False
        task["status"] = "running"
        task["progress"] = 1
        task["progress_message"] = "评测任务已启动…"
        task["error_message"] = None
        _RESULTS[task_id] = []
        view = _progress_view(task)

    runner = asyncio.create_task(_run_eval(task_id))
    async with _LOCK:
        _RUNNERS[task_id] = runner
    return view


async def get_progress(task_id: str) -> dict[str, Any]:
    async with _LOCK:
        task = _TASKS.get(task_id)
        if not task:
            raise KeyError("任务不存在")
        return _progress_view(task)


async def get_results(task_id: str) -> list[dict[str, Any]]:
    async with _LOCK:
        if task_id not in _TASKS:
            raise KeyError("任务不存在")
        return deepcopy(_RESULTS.get(task_id) or [])


async def compare_tasks(task_ids: list[str]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for tid in task_ids:
        async with _LOCK:
            task = _TASKS.get(tid)
            rows = list(_RESULTS.get(tid) or [])
        if not task:
            continue
        name = task.get("name") or tid
        if not rows:
            for metric in ("score", "precision", "recall", "faithfulness"):
                points.append(
                    {"task_id": tid, "task_name": name, "metric": metric, "value": 0.0}
                )
            continue
        for metric in ("score", "precision", "recall", "faithfulness"):
            vals = [float(r.get(metric) or 0) for r in rows]
            avg = round(sum(vals) / max(len(vals), 1), 4)
            points.append(
                {"task_id": tid, "task_name": name, "metric": metric, "value": avg}
            )
    return points


async def _run_eval(task_id: str) -> None:
    async with _LOCK:
        task = _TASKS.get(task_id)
        if not task:
            return
        samples = list(_SAMPLES.get(task_id) or [])
        params = dict(task.get("params") or {})
        kb_id = _kb_id_from_params(params)

    try:
        _kb, doc_id = resolve_kb_doc(kb_id, None)
    except Exception as e:  # noqa: BLE001
        async with _LOCK:
            t = _TASKS.get(task_id)
            if t:
                t["status"] = "failed"
                t["error_message"] = str(e)
                t["progress"] = 0
                t["progress_message"] = f"启动失败: {e}"
        return

    total = max(len(samples), 1)
    rows_out: list[dict[str, Any]] = []
    search_type = "hybrid"

    try:
        for i, sample in enumerate(samples):
            async with _LOCK:
                t = _TASKS.get(task_id)
                if not t or t.get("_cancel"):
                    if t:
                        t["status"] = "failed"
                        t["error_message"] = "任务已取消"
                        t["progress_message"] = "已取消"
                    return
                pct = max(1, int((i / total) * 100))
                t["progress"] = min(99, pct)
                t["progress_message"] = f"评测进行中 {pct}%（{i + 1}/{total}）"

            question = sample.get("question") or ""
            expected = sample.get("expected_answer") or ""
            try:
                hits, meta = await _retrieve_for_eval(
                    kb_id=_kb,
                    doc_id=doc_id,
                    query=question,
                    search_type=search_type,
                    top_n=3,
                )
            except Exception as e:  # noqa: BLE001
                hits, meta = [], {"fallback": str(e)}

            joined = "\n".join(str(h.get("content") or "") for h in (hits or []))
            # 无 LLM 时用检索拼接作为 answer 近似
            answer = joined[:800] if joined.strip() else ""
            score = _overlap_score(expected, answer or joined)
            e_set, a_set = _token_set(expected), _token_set(answer or joined)
            inter = len(e_set & a_set)
            precision = round(inter / max(len(a_set), 1), 4) if a_set else 0.0
            recall = round(inter / max(len(e_set), 1), 4) if e_set else 0.0
            faithfulness = round(min(1.0, score + 0.05), 4) if answer else 0.0
            degraded = (meta or {}).get("fallback") in ("bm25",) or str(
                (meta or {}).get("effective_search_type") or ""
            ).endswith("bm25")
            mode = "keyword" if degraded else "hybrid"
            sources = [
                {
                    "chunk_id": h.get("chunk_id"),
                    "document_id": h.get("doc_id"),
                    "document_name": h.get("source_doc") or "",
                    "content": (h.get("content") or "")[:200],
                    "score": h.get("score"),
                }
                for h in (hits or [])[:3]
            ]
            rows_out.append(
                {
                    "sample_id": sample.get("id"),
                    "question": question,
                    "answer": answer,
                    "expected_answer": expected,
                    "score": score,
                    "precision": precision,
                    "recall": recall,
                    "faithfulness": faithfulness,
                    "detail": "命中期望关键词" if score >= 0.5 else "部分/未命中期望要点",
                    "retrieval_mode": mode,
                    "retrieval_degraded": bool(degraded),
                    "sources": sources,
                }
            )
            await asyncio.sleep(0)

        async with _LOCK:
            t = _TASKS.get(task_id)
            if not t:
                return
            if t.get("_cancel"):
                t["status"] = "failed"
                t["error_message"] = "任务已取消"
                return
            _RESULTS[task_id] = rows_out
            t["status"] = "completed"
            t["progress"] = 100
            t["progress_message"] = "评测完成"
            t["error_message"] = None
    except asyncio.CancelledError:
        async with _LOCK:
            t = _TASKS.get(task_id)
            if t:
                t["status"] = "failed"
                t["error_message"] = "任务已取消"
                t["progress_message"] = "已取消"
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("评测任务失败 %s: %s", task_id, e)
        async with _LOCK:
            t = _TASKS.get(task_id)
            if t:
                t["status"] = "failed"
                t["error_message"] = str(e)
                t["progress_message"] = f"评测失败: {e}"
    finally:
        async with _LOCK:
            _RUNNERS.pop(task_id, None)
