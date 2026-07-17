# -*- coding: utf-8 -*-
"""
智能 RAG 平台 — 数据库一键初始化
与后端 ORM（models.py）对齐：create_all + 种子 admin/admin123
使用：在项目根或任意目录执行 python scripts/init_db.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
load_dotenv(BACKEND / ".env", override=True)

from app import config  # noqa: E402
from app.db.seed import init_schema_and_seed  # noqa: E402

print(f"[init_db] 环境: {config.ENV}")
print(f"[init_db] 数据库: {config.LOCAL_DB_NAME}")

try:
    init_schema_and_seed()
except Exception as e:
    print(f"[init_db] 失败: {e}")
    sys.exit(1)

print("[init_db] 数据库初始化完成！")
print("[init_db] 默认管理员账号: admin / admin123")
