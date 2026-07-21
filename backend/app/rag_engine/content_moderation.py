"""
用户输入敏感词 / 辱骂拦截（后端安全兜底）。

说明：
- 前端有体验层拦截，可被绕过；本模块在 API 入口二次校验
- 词表覆盖常见直白辱骂；谐音/隐晦语义不追求全覆盖
- 命中则阻断请求，不进入检索与 LLM
"""

from __future__ import annotations

import re
from functools import lru_cache

# 直白辱骂词（中英）；与前端 ChatDialog 保持同步
_SENSITIVE_WORDS: tuple[str, ...] = (
    # 原有
    "傻逼",
    "傻叉",
    "傻B",
    "傻b",
    "操你",
    "操你妈",
    "草泥马",
    "他妈的",
    "妈的",
    "去死",
    "滚蛋",
    "混蛋",
    "王八蛋",
    "狗屎",
    "贱人",
    "婊子",
    "智障",
    "脑残",
    # 用户实测漏拦 + 常见变体
    "蠢猪",
    "笨猪",
    "猪狗",
    "狗东西",
    "狗日的",
    "畜生",
    "废物",
    "白痴",
    "蠢材",
    "蠢货",
    "混蛋东西",
    "一坨屎",
    "屎",
    "放屁",
    "恶心",
    "找死",
    "有病",
    "神经病",
    "疯子",
    "去死吧",
    "滚开",
    "滚蛋吧",
    "滚吧",
    # 拼音/缩写（按词边界匹配）
    "sb",
    "2b",
    "cnm",
    "cnmb",
    "nmsl",
    "wdnmd",
    "tmd",
    "nmb",
    "fuck",
    "fucking",
    "shit",
    "bitch",
    "asshole",
    "damn",
    "bastard",
    "idiot",
    "stupid",
)

# 短语/句式（正则），覆盖「你是一坨屎」等组合
_SENSITIVE_REGEX: tuple[str, ...] = (
    r"你是一?坨?屎",
    r"一坨屎",
    r"[你他她]妈的",
    r"去死吧?",
    r"狗日的?",
)

SENSITIVE_BLOCK_MSG = "输入包含不当用语，请修改后再试"


@lru_cache(maxsize=1)
def _compiled_patterns() -> tuple[re.Pattern[str], ...]:
    patterns: list[re.Pattern[str]] = []
    for word in _SENSITIVE_WORDS:
        w = (word or "").strip()
        if not w:
            continue
        escaped = re.escape(w)
        # 含拉丁字母或数字的缩写：按词边界，降低误伤
        if re.search(r"[a-zA-Z0-9]", w):
            patterns.append(re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE))
        else:
            patterns.append(re.compile(escaped, re.IGNORECASE))
    for expr in _SENSITIVE_REGEX:
        patterns.append(re.compile(expr, re.IGNORECASE))
    return tuple(patterns)


def find_sensitive_hit(text: str) -> str | None:
    """若命中敏感词，返回占位码；否则 None。"""
    raw = text or ""
    if not raw.strip():
        return None
    for pattern in _compiled_patterns():
        if pattern.search(raw):
            return "sensitive_word"
    return None


def contains_sensitive(text: str) -> bool:
    return find_sensitive_hit(text) is not None


def check_user_query(text: str) -> tuple[bool, str]:
    """
    校验用户问句。
    返回 (ok, message)：ok=False 时应直接拒绝请求。
    """
    if contains_sensitive(text):
        return False, SENSITIVE_BLOCK_MSG
    return True, ""


def clear_pattern_cache() -> None:
    """测试或热更新词表时清空编译缓存。"""
    _compiled_patterns.cache_clear()
