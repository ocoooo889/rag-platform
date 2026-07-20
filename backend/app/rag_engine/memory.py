"""
短时记忆（会话内 Buffer Memory）

职责：
- 读取最近 N 轮对话，格式化为 prompt 用文本
- 写入本轮 user / assistant 消息

说明：
- 仅覆盖「这一场会话」；不含跨会话长期记忆、不含会话摘要（可后续扩展）
- 底层仍用 sqlite_helper，行为与原先 chat.py 内联逻辑一致
"""

from __future__ import annotations

from app import config
from app.db.sqlite_helper import load_chat_history, save_conversation


class ChatMemory:
    """会话短时记忆：滑动窗口 Buffer。"""

    def __init__(self, max_rounds: int | None = None) -> None:
        # 默认沿用 Day1 定死的多轮上限
        self.max_rounds = int(
            max_rounds
            if max_rounds is not None
            else getattr(config, "MAX_CHAT_HISTORY_ROUNDS", 10) or 10
        )

    def load_turns(self, session_id: str | None) -> list[dict[str, str]]:
        """
        加载最近若干轮消息（按时间正序）。
        无 session 或无历史时返回空列表。
        """
        if not (session_id or "").strip():
            return []
        rows = load_chat_history(session_id.strip(), self.max_rounds)
        out: list[dict[str, str]] = []
        for r in rows:
            out.append({"role": str(r["role"] or ""), "content": str(r["content"] or "")})
        return out

    def as_prompt_text(self, session_id: str | None) -> str:
        """
        生成给 Rewrite / LLM 用的历史文本。
        格式与原先 chat._history_text 一致：每行 `role: content`
        """
        turns = self.load_turns(session_id)
        if not turns:
            return ""
        return "\n".join(f"{t['role']}: {t['content']}" for t in turns)

    def save_user(
        self,
        *,
        msg_id: str,
        session_id: str,
        kb_id: str,
        content: str,
        created_at: str,
    ) -> None:
        """写入用户消息。"""
        save_conversation(msg_id, session_id, kb_id, "user", content, None, created_at)

    def save_assistant(
        self,
        *,
        msg_id: str,
        session_id: str,
        kb_id: str,
        content: str,
        references_json: str | None,
        created_at: str,
    ) -> None:
        """写入助手消息（可带 references JSON）。"""
        save_conversation(
            msg_id,
            session_id,
            kb_id,
            "assistant",
            content,
            references_json,
            created_at,
        )

    def save_turn(
        self,
        *,
        user_msg_id: str,
        assistant_msg_id: str,
        session_id: str,
        kb_id: str,
        user_content: str,
        assistant_content: str,
        references_json: str | None,
        created_at: str,
    ) -> None:
        """一次写入 user + assistant（非流式 /send 用）。"""
        self.save_user(
            msg_id=user_msg_id,
            session_id=session_id,
            kb_id=kb_id,
            content=user_content,
            created_at=created_at,
        )
        self.save_assistant(
            msg_id=assistant_msg_id,
            session_id=session_id,
            kb_id=kb_id,
            content=assistant_content,
            references_json=references_json,
            created_at=created_at,
        )


# 默认单例：接口层直接用，避免到处 new
default_memory = ChatMemory()


def history_for_prompt(session_id: str | None) -> str:
    """便捷函数：等价于原先 _history_text。"""
    return default_memory.as_prompt_text(session_id)
