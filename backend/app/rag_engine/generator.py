"""LLM 对话生成：加载 prompts/rag_chat.prompt"""

from __future__ import annotations

from pathlib import Path

from app.rag_engine.prompt_guard import format_context_chunks, sanitize_chunk_content
from app.utils.llm_client import chat_completion, chat_completion_stream

# 新架子提示词在 backend/prompts/（兼容根目录 prompts/）
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = _BACKEND_ROOT / "prompts" / "rag_chat.prompt"
if not PROMPT_PATH.exists():
    PROMPT_PATH = _BACKEND_ROOT.parent / "prompts" / "rag_chat.prompt"


def _load_template() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "你是知识库专属问答助手。\n"
        "参考片段：\n{{context_chunks}}\n"
        "用户问题：{{query}}\n"
        "无相关信息时回复：当前知识库未查询到相关内容。\n"
    )


def build_messages(
    context_chunks: list[dict],
    query: str,
    chat_history: str = "",
) -> list[dict]:
    context = format_context_chunks(context_chunks)
    safe_query = sanitize_chunk_content(query)

    filled = (
        _load_template()
        .replace("{{chat_history}}", chat_history or "（无历史）")
        .replace("{{context_chunks}}", context)
        .replace("{{query}}", safe_query)
        .replace("{{user_query}}", safe_query)
    )
    return [{"role": "user", "content": filled}]


async def generate_answer(context_chunks: list[dict], query: str, chat_history: str = "") -> str:
    return await chat_completion(build_messages(context_chunks, query, chat_history))


async def generate_answer_stream(context_chunks: list[dict], query: str, chat_history: str = ""):
    async for token in chat_completion_stream(build_messages(context_chunks, query, chat_history)):
        yield token
