import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for name in ["dev_ab_merge_test.db", "dev_shanghuanhuan_rag.db"]:
    p = root / name
    if not p.exists():
        continue
    print("===", name, "===")
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    for r in c.execute("SELECT id, name FROM knowledge_bases LIMIT 8"):
        print("KB", dict(r))
    for r in c.execute(
        "SELECT id, kb_id, filename, status FROM documents ORDER BY rowid DESC LIMIT 15"
    ):
        print("DOC", dict(r))
