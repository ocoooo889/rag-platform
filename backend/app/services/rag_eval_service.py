"""
RAG 黄金集评测服务：封装 run_baseline 逻辑，供 API 调用。
"""

from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.db.sqlite_helper import get_conn, get_document, kb_exists, load_chunks_by_doc
from app.rag_engine.rag_pipeline import RAGPipeline

# 黄金集：问句 + 命中判定关键词
GOLDEN_QUERIES: list[tuple[str, str, list[str]]] = [
    ("Q01", "公司年假有几天？", ["年假", "5", "10", "15"]),
    ("Q02", "怎么申请年假？", ["申请", "审批", "工作日"]),
    ("Q03", "迟到会有什么处罚？", ["迟到", "警告", "事假"]),
    ("Q04", "事假和年假有什么区别？", ["事假", "年假", "带薪"]),
    ("Q05", "去北京出差，住宿标准是多少？", ["住宿", "500", "700", "1000"]),
    ("Q06", "出差坐飞机有什么规定？", ["飞机", "经济舱", "800"]),
    ("Q07", "报销需要哪些材料？", ["发票", "报销"]),
    ("Q08", "系统支持哪几种检索方式？", ["向量", "BM25", "混合"]),
    ("Q09", "混合检索的融合公式是什么？", ["0.7", "alpha", "融合"]),
    ("Q10", "Embedding API 失效了怎么办？", ["降级", "BM25", "关键词"]),
]

RESULTS_DIR = Path(__file__).resolve().parents[3] / "rag-tuning" / "results"


def _hits_ok(hits: list[dict], keywords: list[str]) -> str:
    text = "\n".join(str(h.get("content") or "") for h in (hits or []))
    if not text.strip():
        return "N"
    hit_n = sum(1 for k in keywords if k in text)
    if hit_n >= max(1, len(keywords) // 2):
        return "Y"
    if hit_n > 0:
        return "部分"
    return "N"


def resolve_kb_doc(kb_id: str | None, doc_id: str | None) -> tuple[str, str]:
    """解析评测目标 kb/doc；未指定时自动挑选首个 completed 文档。"""
    if kb_id and doc_id:
        doc = get_document(doc_id)
        if not doc or doc["kb_id"] != kb_id:
            raise ValueError("文档不存在或不属于该知识库")
        if doc["status"] != "completed":
            raise ValueError(f"文档状态为 {doc['status']}，需 completed 后再评测")
        return kb_id, doc_id

    if kb_id and not doc_id:
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT id FROM documents
                WHERE kb_id=? AND status='completed'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (kb_id,),
            ).fetchone()
        if row:
            return kb_id, str(row["id"])
        raise ValueError("该知识库下无 completed 文档")

    # 遍历所有 KB（由调用方保证权限后传入 kb_id 更常见）
    raise ValueError("请指定 kb_id（及可选 doc_id）")


async def _retrieve_for_eval(
    *,
    kb_id: str,
    doc_id: str,
    query: str,
    search_type: str,
    top_n: int,
) -> tuple[list[dict], dict[str, Any]]:
    rows = load_chunks_by_doc(doc_id)
    if not rows:
        return [], {"search_type": search_type, "hits_count": 0}

    texts = [r["content"] for r in rows]
    ids = [r["chroma_id"] or r["id"] for r in rows]
    doc = get_document(doc_id)
    filename = str(doc["filename"]) if doc else ""
    source_docs = [filename] * len(rows)
    doc_ids = [doc_id] * len(rows)

    hits, retrieve_meta = await RAGPipeline.retrieve_only(
        query=query,
        texts=texts,
        ids=ids,
        search_type=search_type,
        top_n=top_n,
        kb_id=kb_id,
        doc_id=doc_id,
        source_docs=source_docs,
        doc_ids=doc_ids,
    )
    meta = {"search_type": search_type, "hits_count": len(hits), **(retrieve_meta or {})}
    return hits, meta


async def run_golden_eval(
    *,
    kb_id: str,
    doc_id: str | None = None,
    modes: list[str] | None = None,
    top_n: int = 3,
    save_csv: bool = True,
) -> dict[str, Any]:
    """
    跑黄金集基线，返回汇总 + 明细；可选写入 rag-tuning/results。
    """
    if not kb_exists(kb_id):
        raise ValueError("知识库不存在")

    resolved_kb, resolved_doc = resolve_kb_doc(kb_id, doc_id)
    valid_modes = {"keyword", "vector", "hybrid"}
    run_modes = [m.strip().lower() for m in (modes or ["keyword", "vector", "hybrid"])]
    for m in run_modes:
        if m not in valid_modes:
            raise ValueError(f"不支持的检索模式: {m}")

    rows: list[dict[str, Any]] = []
    for qid, query, keywords in GOLDEN_QUERIES:
        row: dict[str, Any] = {"id": qid, "query": query}
        for mode in run_modes:
            t0 = time.perf_counter()
            try:
                hits, _meta = await _retrieve_for_eval(
                    kb_id=resolved_kb,
                    doc_id=resolved_doc,
                    query=query,
                    search_type=mode,
                    top_n=top_n,
                )
                mark = _hits_ok(hits, keywords)
                err = None
            except Exception as e:  # noqa: BLE001
                hits = []
                mark = f"ERR:{type(e).__name__}"
                err = str(e)
            ms = round((time.perf_counter() - t0) * 1000, 1)
            row[mode] = mark
            row[f"{mode}_ms"] = ms
            row[f"{mode}_hits"] = len(hits)
            if err:
                row[f"{mode}_error"] = err
        rows.append(row)

    def count_y(key: str) -> int:
        return sum(1 for r in rows if r.get(key) == "Y")

    summary = {
        "kb_id": resolved_kb,
        "doc_id": resolved_doc,
        "top_n": top_n,
        "modes": run_modes,
        "total_questions": len(GOLDEN_QUERIES),
    }
    for mode in run_modes:
        summary[f"{mode}_y"] = count_y(mode)

    result: dict[str, Any] = {
        "summary": summary,
        "rows": rows,
        "csv_path": None,
    }

    if save_csv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = RESULTS_DIR / f"baseline-api-{stamp}.csv"
        fields = ["id", "query"]
        for mode in run_modes:
            fields.extend([mode, f"{mode}_ms", f"{mode}_hits"])
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        result["csv_path"] = str(out)

    return result
