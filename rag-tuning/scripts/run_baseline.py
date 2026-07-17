"""
第 0 步辅助：对黄金问句打 keyword/vector/hybrid，判断 Top3 是否含预期关键词。

用法（在 rag-platform 根目录，后端已起在 8001）：

  python rag-tuning/scripts/run_baseline.py
  python rag-tuning/scripts/run_baseline.py --kb-id kbxxx --doc-id dxxx

环境变量可选：BASE_URL / ADMIN_USER / ADMIN_PASS / KB_ID / DOC_ID
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# 黄金集：问句 + 命中判定关键词（任一命中即算 Y；可按文档微调）
GOLDEN = [
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


def req(base: str, method: str, path: str, body=None, token: str | None = None):
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}


def hits_ok(hits: list, keywords: list[str]) -> str:
    text = "\n".join(str(h.get("content") or "") for h in (hits or []))
    if not text.strip():
        return "N"
    hit_n = sum(1 for k in keywords if k in text)
    if hit_n >= max(1, len(keywords) // 2):
        return "Y"
    if hit_n > 0:
        return "部分"
    return "N"


def pick_kb_doc(base: str, token: str, kb_id: str | None, doc_id: str | None):
    if kb_id and doc_id:
        return kb_id, doc_id

    st, kbs = req(base, "GET", "/api/knowledge-bases", token=token)
    if st != 200 or kbs.get("code") != 0:
        raise RuntimeError(f"拉知识库失败: {kbs}")
    data = kbs.get("data")
    items = data.get("items") if isinstance(data, dict) else data
    if not items:
        raise RuntimeError("没有任何知识库，请先上传 demo 文档")

    # 优先找有 completed 文档的 KB
    for kb in items:
        kid = kb.get("id")
        st, docs = req(base, "GET", f"/api/knowledge-bases/{kid}/documents", token=token)
        if st != 200:
            continue
        ddata = docs.get("data")
        ditems = ddata.get("items") if isinstance(ddata, dict) else ddata
        for d in ditems or []:
            if d.get("status") == "completed":
                print(f"[auto] kb={kid} doc={d.get('id')} file={d.get('filename')}")
                return kid, d.get("id")

    raise RuntimeError("未找到 status=completed 的文档，请先完成入库")


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG 调优第0步：黄金集基线跑批")
    parser.add_argument("--base", default=os.getenv("BASE_URL", "http://127.0.0.1:8001"))
    parser.add_argument("--user", default=os.getenv("ADMIN_USER", "admin"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASS", "admin123"))
    parser.add_argument("--kb-id", default=os.getenv("KB_ID"))
    parser.add_argument("--doc-id", default=os.getenv("DOC_ID"))
    args = parser.parse_args()

    st, health = req(args.base, "GET", "/health")
    if st != 200:
        print("后端未就绪，请先启动 uvicorn :8001")
        return 1
    print("[ok] health", health.get("data"))

    st, login = req(
        args.base,
        "POST",
        "/api/auth/login/json",
        {"username": args.user, "password": args.password},
    )
    token = (login.get("data") or {}).get("access_token")
    if not token:
        print("登录失败", login)
        return 1
    print("[ok] login")

    try:
        kb_id, doc_id = pick_kb_doc(args.base, token, args.kb_id, args.doc_id)
    except RuntimeError as e:
        print("[fail]", e)
        return 1

    rows = []
    modes = ["keyword", "vector", "hybrid"]
    for qid, query, keywords in GOLDEN:
        row = {"id": qid, "query": query}
        for mode in modes:
            t0 = time.perf_counter()
            st, body = req(
                args.base,
                "POST",
                "/api/rag/test_retrieve",
                {
                    "kb_id": kb_id,
                    "doc_id": doc_id,
                    "search_type": mode,
                    "query": query,
                    "top_n": 3,
                },
                token=token,
            )
            ms = round((time.perf_counter() - t0) * 1000, 1)
            hits = ((body.get("data") or {}).get("hits") or []) if isinstance(body, dict) else []
            mark = hits_ok(hits, keywords) if body.get("code") == 0 else f"ERR:{body.get('code')}"
            row[mode] = mark
            row[f"{mode}_ms"] = ms
            row[f"{mode}_hits"] = len(hits)
            print(f"{qid} {mode:8s} {mark:4s} hits={len(hits)} ms={ms}")
        rows.append(row)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"baseline-{stamp}.csv"
    fields = [
        "id",
        "query",
        "keyword",
        "vector",
        "hybrid",
        "keyword_ms",
        "vector_ms",
        "hybrid_ms",
        "keyword_hits",
        "vector_hits",
        "hybrid_hits",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # 汇总
    def count_y(key: str) -> int:
        return sum(1 for r in rows if r.get(key) == "Y")

    print("==== SUMMARY ====")
    print(f"keyword Y={count_y('keyword')}/10  vector Y={count_y('vector')}/10  hybrid Y={count_y('hybrid')}/10")
    print(f"CSV -> {out}")
    print("请把结果抄到 rag-tuning/01-评测基线表.md，加压 ★ 五条需手工在对话页测多轮。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
