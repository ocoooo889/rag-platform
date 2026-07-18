"""多轮对话 Query Rewrite：生成独立检索问句（失败回退原句）"""

from __future__ import annotations

import logging
from pathlib import Path

from app import config
from app.utils.llm_client import LLMServiceError, chat_completion

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_PROMPT_PATH = _BACKEND_ROOT / "prompts" / "standalone_query.prompt"


def _load_prompt() -> str:
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "根据对话历史，将最新问题改写成独立完整的检索问句，只输出问句。\n"
        "历史：{{chat_history}}\n问题：{{query}}\n"
    )


def _clean_rewritten(text: str, fallback: str) -> str:
    """清洗模型输出；非法或过长时回退原句"""
    if not text:
        return fallback
    line = text.strip().splitlines()[0].strip()
    # 去掉常见包裹符号
    if (line.startswith("「") and line.endswith("」")) or (
        line.startswith("“") and line.endswith("”")
    ):
        line = line[1:-1].strip()
    if line.startswith('"') and line.endswith('"'):
        line = line[1:-1].strip()
    if not line or len(line) > 200:
        return fallback
    return line


async def rewrite_query_for_retrieve(query: str, chat_history: str = "") -> str:
    """
    有历史时把追问改写成 standalone query 供检索；无历史或失败则返回原 query。
    生成回答仍应使用用户原始 query。
    """
    q = (query or "").strip()
    if not q:
        return q

    # 环境开关：ENABLE_QUERY_REWRITE=false 可关闭
    enabled = str(getattr(config, "ENABLE_QUERY_REWRITE", True)).lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    if not enabled:
        return q

    history = (chat_history or "").strip()
    if not history or history in {"（无历史）", "(无历史)"}:
        return q

    prompt = (
        _load_prompt()
        .replace("{{chat_history}}", history)
        .replace("{{query}}", q)
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        rewritten = await chat_completion(messages)
        out = _clean_rewritten(rewritten, q)
        if out != q:
            logger.info("Query Rewrite: %r -> %r", q[:80], out[:80])
        return out
    except LLMServiceError as e:
        logger.warning("Query Rewrite 失败，回退原句: %s", e.message)
        return q
    except Exception as e:
        logger.warning("Query Rewrite 异常，回退原句: %s", e)
        return q
