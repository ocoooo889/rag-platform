"""
3号独立自测脚本（不依赖前端 / 4号上传页）
步骤：
  1. 初始化数据库
  2. 写入演示知识库 + 文档行
  3. 切片向量化入库
  4. 调用三种检索打印结果

用法（在 rag-platform 根目录）：
  python scripts/init_db.py
  python scripts/self_test_rag.py
"""

from __future__ import annotations

import asyncio
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app import config  # noqa: E402
from app.rag_engine.ingest import ingest_document  # noqa: E402
from app.rag_engine.retriever import retrieve  # noqa: E402
from app.db.sqlite_helper import load_chunks_by_doc  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def seed_kb_and_doc(md_path: Path) -> tuple[str, str]:
    kb_id, doc_id = "kb_demo001", "doc_demo001"
    db = ROOT / config.LOCAL_DB_NAME
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO knowledge_bases (id, name, description, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (kb_id, "演示知识库", "3号自测用", _now()),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO documents
        (id, kb_id, filename, file_type, file_size, status, chunk_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc_id, kb_id, md_path.name, "md", md_path.stat().st_size,
            "pending", 0, _now(),
        ),
    )
    conn.commit()
    conn.close()
    return kb_id, doc_id


async def main():
    print("=" * 50)
    print("3号 RAG 自测")
    print(f"ENV={config.ENV}")
    print(f"DB={config.LOCAL_DB_NAME}")
    print(f"Chroma集合={config.CHROMA_COLLECTION_NAME}")
    print(f"API Key 已配置={bool(config.OPENAI_API_KEY) and not config.OPENAI_API_KEY.startswith('sk-xxxx')}")
    print("=" * 50)

    md = ROOT / "demo-materials" / "测试文档1-公司考勤制度.md"
    if not md.exists():
        print(f"[失败] 找不到演示文档: {md}")
        return

    kb_id, doc_id = seed_kb_and_doc(md)
    print(f"[1] 已写入知识库/文档: {kb_id} / {doc_id}")

    try:
        n = await ingest_document(kb_id, doc_id, str(md), filename=md.name)
        print(f"[2] 入库成功，切片数={n}")
    except Exception as e:
        print(f"[2] 入库失败: {e}")
        import traceback
        traceback.print_exc()
        print("    若提示 Chroma/Embedding：请先启动 chroma，并在 .env 填真实 OPENAI_API_KEY")
        return

    rows = load_chunks_by_doc(doc_id)
    texts = [r["content"] for r in rows]
    ids = [r["chroma_id"] for r in rows]
    source_docs = [md.name] * len(rows)
    doc_ids = [doc_id] * len(rows)

    query = "公司年假有几天？"
    print(f"[3] 测试问题: {query}")
    for st in ("vector", "keyword", "hybrid"):
        hits = await retrieve(
            query, texts, ids, st, 3,
            doc_id=doc_id, kb_id=kb_id,
            source_docs=source_docs, doc_ids=doc_ids,
        )
        print(f"\n--- {st} ---")
        for i, h in enumerate(hits, 1):
            preview = (h.get("content") or "")[:60].replace("\n", " ")
            # 去掉 BOM 等特殊字符，避免 Windows 控制台 GBK 打印报错
        safe = preview.replace("\ufeff", "").encode("gbk", errors="ignore").decode("gbk")
        print(f"  #{i} score={h.get('score')}  {safe}...")

    print("\n[完成] 下一步：")
    print("  cd backend")
    print("  uvicorn app.main:app --reload --port 8001")
    print("  浏览器打开 http://localhost:8001/docs 测 POST /api/rag/test_retrieve")
    print(f"  请求体示例 kb_id={kb_id}, doc_id={doc_id}")


if __name__ == "__main__":
    asyncio.run(main())
