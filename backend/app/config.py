"""
智能 RAG 平台 — 全局配置（6号负责人 · 定死参数）
注意：勿在文件中直接修改 Key，Key 统一从 .env 加载。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 优先加载项目根 / backend 下的 .env，兼容多种启动目录
# override=True：项目 .env 覆盖系统环境变量（避免本机 LLM_MODEL=gpt-5.1 盖住百炼 qwen-plus）
_ROOT = Path(__file__).resolve().parents[2]  # rag-platform/
load_dotenv(_ROOT / ".env", override=True)
load_dotenv(_ROOT / "backend" / ".env", override=True)
load_dotenv(override=False)

# ============================================================
# [定死] Embedding 模型与向量维度（Day1 定死，不可改）
# ============================================================
# 可用 .env 覆盖；接百炼时用 text-embedding-v4，维度仍对齐 1536
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
EMBEDDING_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", "10"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))

# ============================================================
# [定死] 切片参数（Day1 定死，不可改）
# ============================================================
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SEPARATORS = ["\n## ", "\n### ", "\n", "。", ".", " "]

# ============================================================
# [定死] 多轮对话历史限制
# ============================================================
MAX_CHAT_HISTORY_ROUNDS = 10  # 多轮对话最多保留轮数（超出自动截断最早的消息）
# ============================================================
# [定死] LLM 模型配置
# ============================================================
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "10"))
LLM_MAX_RETRIES = 1

# ============================================================
# [定死] 混合检索加权因子（Hybrid Score Formula）
# ============================================================
HYBRID_ALPHA = 0.7  # 向量权重 0.7
BM25_WEIGHT = 0.3   # 全文权重 0.3（= 1 - HYBRID_ALPHA）
DEFAULT_TOP_N = 3
MAX_TOP_N = 10

# ============================================================
# 环境隔离 · 个人标识
# ============================================================
ENV = os.getenv("ENV", "dev-default")
LOCAL_DB_NAME = os.getenv("LOCAL_DB_NAME", f"{ENV}_rag.db")
CHROMA_COLLECTION_SUFFIX = os.getenv("CHROMA_COLLECTION_SUFFIX", "default")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", f"./uploads/{ENV}")

# ============================================================
# 数据库
# ============================================================
DATABASE_URL = f"sqlite:///./{LOCAL_DB_NAME}"

# ============================================================
# Chroma 向量库
# ============================================================
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION_NAME = f"rag_chunks_{CHROMA_COLLECTION_SUFFIX}"

# ============================================================
# LLM / Embedding API（支持从系统环境变量 DASHSCOPE_API_KEY 回退）
# ============================================================
def _clean_secret(value: str | None) -> str:
    """去掉首尾空白与成对引号，避免 .env 写成 KEY=\"xxx\" 导致鉴权失败。"""
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text


OPENAI_API_KEY = _clean_secret(
    os.getenv("OPENAI_API_KEY")
    or os.getenv("DASHSCOPE_API_KEY")
    or os.getenv("LLM_API_KEY")
    or ""
)
_default_base = "https://api.openai.com/v1"
_has_dashscope = bool(_clean_secret(os.getenv("DASHSCOPE_API_KEY"))) or (
    "dashscope" in (os.getenv("OPENAI_BASE_URL") or "").lower()
)
if _has_dashscope and not os.getenv("OPENAI_BASE_URL"):
    _default_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", _default_base)
# 百炼兼容模式下若未显式指定，默认百炼模型（避免落到 gpt-4o-mini）
if "dashscope" in (OPENAI_BASE_URL or "").lower():
    if not os.getenv("EMBEDDING_MODEL"):
        EMBEDDING_MODEL = "text-embedding-v4"
    if not os.getenv("LLM_MODEL"):
        LLM_MODEL = "qwen-plus"

# ============================================================
# JWT 鉴权
# ============================================================
JWT_SECRET = os.getenv("JWT_SECRET", "rag-platform-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# ============================================================
# FastAPI 服务
# ============================================================
API_HOST = "0.0.0.0"
API_PORT = 8001

# ============================================================
# V2：Langfuse LLM 可观测（后端 A；未配置则自动跳过上报）
# ============================================================
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
