"""
Prompt 注入防护：用户输入过滤、检索片段清洗、上下文分隔。

说明：
- 默认仅做轻量规则过滤，不阻断正常业务问句
- 命中可疑模式时记录 warnings，供接口 meta 回显
"""

from __future__ import annotations

import re
from typing import Any

# 常见注入/越权指令（中英）
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)ignore\s+(all\s+)?(previous|above)\s+instructions?"), "ignore_instructions"),
    (re.compile(r"(?i)disregard\s+(the\s+)?(system|above)"), "disregard_system"),
    (re.compile(r"(?i)you\s+are\s+now\s+(a|an)\s+"), "role_override"),
    (re.compile(r"(?i)\bsystem\s*:\s*"), "system_prefix"),
    (re.compile(r"(?i)\bassistant\s*:\s*"), "assistant_prefix"),
    (re.compile(r"忽略(以上|先前|之前).{0,8}(指令|规则|约束)"), "ignore_instructions_zh"),
    (re.compile(r"无视.{0,6}(系统|规则|约束)"), "disregard_system_zh"),
    (re.compile(r"你现在是.{0,12}(助手|AI|专家)"), "role_override_zh"),
    (re.compile(r"<\s*/?\s*(system|assistant|instruction)\s*>", re.I), "xml_role_tag"),
]

# 片段内疑似「假系统消息」行
_CHUNK_LINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?im)^\s*(system|assistant|user)\s*:\s*"),
    re.compile(r"(?im)^\s*#\s*(系统|角色|指令)\s*"),
    re.compile(r"(?im)ignore\s+(all\s+)?previous", re.I),
    re.compile(r"忽略.{0,6}指令"),
]


def _scan_patterns(text: str, patterns: list[tuple[re.Pattern[str], str]]) -> list[str]:
    warnings: list[str] = []
    for pattern, code in patterns:
        if pattern.search(text or ""):
            warnings.append(code)
    return warnings


def sanitize_user_query(query: str) -> tuple[str, list[str]]:
    """
    清洗用户问句：去掉首尾空白、折叠极端重复分隔符。
    返回 (清洗后文本, 警告码列表)。
    """
    raw = (query or "").strip()
    if not raw:
        return "", []

    warnings = _scan_patterns(raw, _INJECTION_PATTERNS)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", raw)
    cleaned = re.sub(r"(?m)^\s*(system|assistant)\s*:\s*", "", cleaned, flags=re.I)
    return cleaned.strip() or raw, warnings


def sanitize_chunk_content(content: str) -> str:
    """清洗检索片段，弱化文档内嵌指令对模型的影响。"""
    text = (content or "").strip()
    if not text:
        return ""

    lines: list[str] = []
    for line in text.splitlines():
        drop = False
        for pat in _CHUNK_LINE_PATTERNS:
            if pat.search(line):
                drop = True
                break
        if not drop:
            lines.append(line)
    cleaned = "\n".join(lines).strip()
    return cleaned or text


def sanitize_hits(hits: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """批量清洗检索命中片段的 content 字段。"""
    out: list[dict[str, Any]] = []
    for h in hits or []:
        item = dict(h)
        if item.get("content"):
            item["content"] = sanitize_chunk_content(str(item["content"]))
        out.append(item)
    return out


def format_context_chunks(chunks: list[dict[str, Any]]) -> str:
    """
    用明确分隔符包裹每个片段，降低与系统提示混淆的风险。
    """
    if not chunks:
        return "（无检索结果）"

    parts: list[str] = []
    for i, chunk in enumerate(chunks):
        body = sanitize_chunk_content(str(chunk.get("content") or ""))
        source = str(chunk.get("source_doc") or "").strip()
        header = f"[片段{i + 1}]"
        if source:
            header += f" 来源:{source}"
        parts.append(f"<doc {header}>\n{body}\n</doc>")
    return "\n\n".join(parts)
