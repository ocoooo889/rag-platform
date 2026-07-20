"""
意图识别（规则版）— 对话链路检索前路由。

与 Query Rewrite 的区别：
- Rewrite：多轮指代改写成独立检索句
- Intent：判断走 RAG / 闲聊直答 / 系统说明，避免无意义检索

标签：
- knowledge_qa  知识库问答（默认，走检索）
- summarize     总结类（仍走检索，meta 标注）
- compare       对比类（仍走检索，meta 标注）
- chitchat      寒暄致谢（跳过检索）
- meta_help     能力说明（跳过检索）
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from app import config

INTENT_KNOWLEDGE = "knowledge_qa"
INTENT_SUMMARIZE = "summarize"
INTENT_COMPARE = "compare"
INTENT_CHITCHAT = "chitchat"
INTENT_META = "meta_help"

# 整句寒暄 / 致谢 / 告别（避免「你好，年假怎么请」误判）
_GREET_RE = re.compile(
    r"^(你好|您好|嗨|哈喽|hello|hi|hey|早上好|中午好|下午好|晚上好)"
    r"[\s!！。.~～？?]*$",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(
    r"^(谢谢|感谢|多谢|谢谢你|谢谢您|thanks|thank\s*you|thx)"
    r"[\s!！。.~～]*$",
    re.IGNORECASE,
)
_BYE_RE = re.compile(
    r"^(再见|拜拜|回见|bye|goodbye|see\s*you)[\s!！。.~～]*$",
    re.IGNORECASE,
)
_META_RE = re.compile(
    r"^(你是谁|你叫什么|你能做什么|你有什么功能|怎么用|帮助|help|"
    r"介绍一下你自己|你是人工智能吗)[\s!！。.~～？?]*$",
    re.IGNORECASE,
)
_SUMMARIZE_RE = re.compile(r"(总结|概括|摘要|简述|归纳).{0,8}(一下|下|内容|文档|全文)?")
_COMPARE_RE = re.compile(r"(对比|比较|区别|差异|不同点|有何不同)")


@dataclass
class IntentResult:
    label: str
    source: str
    skip_retrieve: bool
    confidence: float
    reply: str | None = None

    def to_meta(self) -> dict[str, Any]:
        data = asdict(self)
        # reply 可能较长，meta 只留是否有直答
        data["has_direct_reply"] = bool(self.reply)
        data.pop("reply", None)
        return data


_CHITCHAT_REPLIES = {
    "greet": "你好！我是知识库问答助手，可以直接问我制度、流程或文档里的问题。",
    "thanks": "不客气。还有其他问题随时问我。",
    "bye": "再见，祝你工作顺利。",
}
_META_REPLY = (
    "我是本平台的知识库问答助手，可以基于你选中的知识库检索并回答问题，"
    "也支持多轮追问。请尽量用具体问题提问，例如「年假有多少天？」。"
)


def _enabled() -> bool:
    return str(getattr(config, "ENABLE_INTENT_ROUTE", True)).lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def classify_intent(query: str) -> IntentResult:
    """
    识别用户意图。关闭开关时一律 knowledge_qa（保持旧行为）。
    """
    q = (query or "").strip()
    if not _enabled():
        return IntentResult(
            label=INTENT_KNOWLEDGE,
            source="disabled",
            skip_retrieve=False,
            confidence=1.0,
        )
    if not q:
        return IntentResult(
            label=INTENT_KNOWLEDGE,
            source="rules",
            skip_retrieve=False,
            confidence=1.0,
        )

    if _GREET_RE.match(q):
        return IntentResult(
            label=INTENT_CHITCHAT,
            source="rules",
            skip_retrieve=True,
            confidence=0.99,
            reply=_CHITCHAT_REPLIES["greet"],
        )
    if _THANKS_RE.match(q):
        return IntentResult(
            label=INTENT_CHITCHAT,
            source="rules",
            skip_retrieve=True,
            confidence=0.99,
            reply=_CHITCHAT_REPLIES["thanks"],
        )
    if _BYE_RE.match(q):
        return IntentResult(
            label=INTENT_CHITCHAT,
            source="rules",
            skip_retrieve=True,
            confidence=0.99,
            reply=_CHITCHAT_REPLIES["bye"],
        )
    if _META_RE.match(q):
        return IntentResult(
            label=INTENT_META,
            source="rules",
            skip_retrieve=True,
            confidence=0.95,
            reply=_META_REPLY,
        )

    # 总结 / 对比：仍走 RAG，仅打标签便于观测与后续策略
    if _COMPARE_RE.search(q):
        return IntentResult(
            label=INTENT_COMPARE,
            source="rules",
            skip_retrieve=False,
            confidence=0.8,
        )
    if _SUMMARIZE_RE.search(q):
        return IntentResult(
            label=INTENT_SUMMARIZE,
            source="rules",
            skip_retrieve=False,
            confidence=0.8,
        )

    return IntentResult(
        label=INTENT_KNOWLEDGE,
        source="rules",
        skip_retrieve=False,
        confidence=0.6,
    )
