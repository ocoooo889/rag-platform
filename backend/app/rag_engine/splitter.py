"""
文档切片：支持多种策略（上传时可选手动选择）。

策略：
- fixed：固定长度
- recursive：递归字符（默认，兼容 Day1 500/50）
- markdown_header：按 Markdown 标题
- paragraph：按段落
- sentence：按句子再拼块
- semantic：语义相似度边界（需 Embedding）
- parent_child：小块检索、大块入库（父子）
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app import config

logger = logging.getLogger(__name__)

# 前端/API 可选策略
SPLIT_STRATEGIES: dict[str, dict[str, str]] = {
    "recursive": {
        "label": "递归切分",
        "desc": "优先按标题/段落/句子边界切，默认兼容 Day1",
    },
    "fixed": {
        "label": "固定长度",
        "desc": "按固定字符数硬切，适合快速对比实验",
    },
    "markdown_header": {
        "label": "按标题切分",
        "desc": "按 # / ## / ### 章节切，适合手册、规范",
    },
    "paragraph": {
        "label": "按段落切分",
        "desc": "按空行分段，过长段落再二次切",
    },
    "sentence": {
        "label": "按句子切分",
        "desc": "按句号等断句后拼到目标长度",
    },
    "semantic": {
        "label": "语义切分",
        "desc": "按句子语义相似度找主题边界（入库较慢）",
    },
    "parent_child": {
        "label": "父子块切分",
        "desc": "子块向量检索，入库内容用父块上下文",
    },
}

DEFAULT_STRATEGY = "recursive"


@dataclass
class SplitOptions:
    """切分参数；未传则用 config 默认。"""

    strategy: str = DEFAULT_STRATEGY
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    # parent_child：父块大小
    parent_chunk_size: int | None = None
    parent_chunk_overlap: int | None = None
    # semantic：相邻句相似度低于此阈值则切分
    semantic_threshold: float | None = None

    def resolved_size(self) -> int:
        return int(self.chunk_size or config.CHUNK_SIZE or 500)

    def resolved_overlap(self) -> int:
        size = self.resolved_size()
        ov = int(
            self.chunk_overlap
            if self.chunk_overlap is not None
            else (config.CHUNK_OVERLAP or 50)
        )
        return max(0, min(ov, max(size - 1, 0)))

    def normalized_strategy(self) -> str:
        key = (self.strategy or DEFAULT_STRATEGY).strip().lower()
        return key if key in SPLIT_STRATEGIES else DEFAULT_STRATEGY

    def to_meta(self) -> dict[str, Any]:
        return {
            "strategy": self.normalized_strategy(),
            "chunk_size": self.resolved_size(),
            "chunk_overlap": self.resolved_overlap(),
            "parent_chunk_size": self.parent_chunk_size,
            "parent_chunk_overlap": self.parent_chunk_overlap,
            "semantic_threshold": self.semantic_threshold,
        }


@dataclass
class SplitResult:
    """texts：写入 SQLite / 喂给 LLM；embed_texts：向量化文本（可与 texts 不同）。"""

    texts: list[str]
    embed_texts: list[str] | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def vectors_source(self) -> list[str]:
        return self.embed_texts if self.embed_texts is not None else self.texts


def list_split_strategies() -> list[dict[str, Any]]:
    """
    供前端下拉：含 is_default 与推荐块参数（来自服务端 config，禁止前端写死）。
    兼容字段：value/key、desc/description。
    """
    default_key = str(getattr(config, "DEFAULT_SPLIT_STRATEGY", None) or DEFAULT_STRATEGY)
    if default_key not in SPLIT_STRATEGIES:
        default_key = DEFAULT_STRATEGY

    chunk_size = int(getattr(config, "CHUNK_SIZE", None) or 500)
    chunk_overlap = int(getattr(config, "CHUNK_OVERLAP", None) or 50)
    # 与 kb index-config / 上传校验对齐
    size_min, size_max = 100, 2000

    items: list[dict[str, Any]] = []
    for key, info in SPLIT_STRATEGIES.items():
        row: dict[str, Any] = {
            "value": key,
            "key": key,
            "label": info["label"],
            "desc": info["desc"],
            "description": info["desc"],
            "is_default": key == default_key,
            "default_chunk_size": chunk_size,
            "default_chunk_overlap": min(chunk_overlap, max(chunk_size - 1, 0)),
            "chunk_size_min": size_min,
            "chunk_size_max": size_max,
            "chunk_overlap_min": 0,
        }
        if key == "parent_child":
            parent_size = int(os.getenv("PARENT_CHUNK_SIZE", "1500"))
            parent_ov = int(os.getenv("PARENT_CHUNK_OVERLAP", "100"))
            row["default_parent_chunk_size"] = parent_size
            row["default_parent_chunk_overlap"] = parent_ov
            row["parent_chunk_size_min"] = 300
            row["parent_chunk_size_max"] = 8000
        if key == "semantic":
            row["default_semantic_threshold"] = float(
                os.getenv("SEMANTIC_SPLIT_THRESHOLD", "0.55")
            )
            row["semantic_threshold_min"] = 0.1
            row["semantic_threshold_max"] = 0.95
        items.append(row)
    return items



def parse_split_options(
    *,
    strategy: str | None = None,
    chunk_size: int | str | None = None,
    chunk_overlap: int | str | None = None,
    parent_chunk_size: int | str | None = None,
    parent_chunk_overlap: int | str | None = None,
    semantic_threshold: float | str | None = None,
) -> SplitOptions:
    def _int(v, default=None):
        if v is None or v == "":
            return default
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def _float(v, default=None):
        if v is None or v == "":
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    return SplitOptions(
        strategy=(strategy or DEFAULT_STRATEGY),
        chunk_size=_int(chunk_size),
        chunk_overlap=_int(chunk_overlap),
        parent_chunk_size=_int(parent_chunk_size),
        parent_chunk_overlap=_int(parent_chunk_overlap),
        semantic_threshold=_float(semantic_threshold),
    )


def _recursive_splitter(size: int, overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=list(getattr(config, "SEPARATORS", None) or ["\n## ", "\n### ", "\n", "。", ".", " "]),
        length_function=len,
    )


def _split_fixed(text: str, size: int, overlap: int) -> list[str]:
    raw = text or ""
    if not raw.strip():
        return []
    if size <= 0:
        return [raw.strip()]
    step = max(size - overlap, 1)
    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        piece = raw[i : i + size].strip()
        if piece:
            out.append(piece)
        if i + size >= n:
            break
        i += step
    return out


def _split_markdown_header(text: str, size: int, overlap: int) -> list[str]:
    headers = [("#", "h1"), ("##", "h2"), ("###", "h3")]
    try:
        md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
        docs = md_splitter.split_text(text or "")
    except Exception as e:
        logger.warning("Markdown 标题切分失败，回退 recursive: %s", e)
        return _recursive_splitter(size, overlap).split_text(text or "")

    out: list[str] = []
    for doc in docs:
        meta = getattr(doc, "metadata", {}) or {}
        header_bits = [str(meta[k]) for k in ("h1", "h2", "h3") if meta.get(k)]
        body = (getattr(doc, "page_content", None) or str(doc) or "").strip()
        if not body:
            continue
        prefix = (" / ".join(header_bits) + "\n") if header_bits else ""
        merged = (prefix + body).strip()
        if len(merged) <= size:
            out.append(merged)
        else:
            # 单节过长再递归切，并尽量保留标题前缀
            parts = _recursive_splitter(size, overlap).split_text(body)
            for p in parts:
                chunk = (prefix + p).strip() if prefix else p.strip()
                if chunk:
                    out.append(chunk)
    return out


def _split_paragraph(text: str, size: int, overlap: int) -> list[str]:
    paras = re.split(r"\n\s*\n+", text or "")
    paras = [p.strip() for p in paras if p and p.strip()]
    if not paras:
        return []
    out: list[str] = []
    buf = ""
    for p in paras:
        if len(p) > size:
            if buf:
                out.append(buf.strip())
                buf = ""
            out.extend(_recursive_splitter(size, overlap).split_text(p))
            continue
        candidate = f"{buf}\n\n{p}".strip() if buf else p
        if len(candidate) <= size:
            buf = candidate
        else:
            if buf:
                out.append(buf.strip())
            buf = p
    if buf.strip():
        out.append(buf.strip())
    return out


_SENT_SPLIT = re.compile(r"(?<=[。！？；.!?;])\s*|\n+")


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENT_SPLIT.split(text or "") if s and s.strip()]
    return parts


def _split_sentence_chunks(text: str, size: int, overlap: int) -> list[str]:
    sents = _split_sentences(text)
    if not sents:
        return []
    out: list[str] = []
    buf = ""
    for s in sents:
        if len(s) > size:
            if buf:
                out.append(buf.strip())
                buf = ""
            out.extend(_recursive_splitter(size, overlap).split_text(s))
            continue
        candidate = f"{buf}{s}" if buf else s
        if len(candidate) <= size:
            buf = candidate
        else:
            if buf:
                out.append(buf.strip())
            # 简单重叠：把上一块尾部若干字带入
            if overlap > 0 and out:
                tail = out[-1][-overlap:]
                buf = f"{tail}{s}"
                if len(buf) > size:
                    buf = s
            else:
                buf = s
    if buf.strip():
        out.append(buf.strip())
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na <= 0 or nb <= 0:
        return 0.0
    return float(dot / (na * nb))


async def _split_semantic(text: str, size: int, overlap: int, threshold: float) -> list[str]:
    """
    按相邻句 Embedding 相似度切分；失败则回退 sentence。
    """
    sents = _split_sentences(text)
    if len(sents) <= 1:
        return _split_sentence_chunks(text, size, overlap)

    try:
        from app.utils.llm_client import get_embeddings_batch

        vectors = await get_embeddings_batch(sents)
    except Exception as e:
        logger.warning("语义切分 Embedding 失败，回退按句子: %s", e)
        return _split_sentence_chunks(text, size, overlap)

    if len(vectors) != len(sents):
        return _split_sentence_chunks(text, size, overlap)

    groups: list[list[str]] = [[sents[0]]]
    for i in range(1, len(sents)):
        sim = _cosine(vectors[i - 1], vectors[i])
        if sim < threshold:
            groups.append([sents[i]])
        else:
            groups[-1].append(sents[i])

    out: list[str] = []
    for g in groups:
        block = "".join(g).strip()
        if not block:
            continue
        if len(block) <= size:
            out.append(block)
        else:
            out.extend(_recursive_splitter(size, overlap).split_text(block))
    return out


def _split_parent_child(
    text: str,
    child_size: int,
    child_overlap: int,
    parent_size: int,
    parent_overlap: int,
) -> SplitResult:
    """
    父块：大窗口；子块：小窗口。
    - embed_texts = 子块（检索更准）
    - texts = 对应父块全文（生成时上下文更全）
    """
    parents = _recursive_splitter(parent_size, parent_overlap).split_text(text or "")
    store: list[str] = []
    embeds: list[str] = []
    for parent in parents:
        parent = (parent or "").strip()
        if not parent:
            continue
        children = _recursive_splitter(child_size, child_overlap).split_text(parent)
        if not children:
            children = [parent]
        for child in children:
            c = (child or "").strip()
            if not c:
                continue
            embeds.append(c)
            store.append(parent)
    return SplitResult(texts=store, embed_texts=embeds)


async def split_text_async(text: str, options: SplitOptions | None = None) -> SplitResult:
    """异步切分（semantic 需要 Embedding）。"""
    opts = options or SplitOptions()
    strategy = opts.normalized_strategy()
    size = opts.resolved_size()
    overlap = opts.resolved_overlap()
    meta = opts.to_meta()

    raw = text or ""
    if not raw.strip():
        return SplitResult(texts=[], meta=meta)

    if strategy == "fixed":
        chunks = _split_fixed(raw, size, overlap)
    elif strategy == "markdown_header":
        chunks = _split_markdown_header(raw, size, overlap)
    elif strategy == "paragraph":
        chunks = _split_paragraph(raw, size, overlap)
    elif strategy == "sentence":
        chunks = _split_sentence_chunks(raw, size, overlap)
    elif strategy == "semantic":
        thr = float(opts.semantic_threshold if opts.semantic_threshold is not None else 0.55)
        meta["semantic_threshold"] = thr
        chunks = await _split_semantic(raw, size, overlap, thr)
    elif strategy == "parent_child":
        parent_size = int(opts.parent_chunk_size or max(size * 3, 1200))
        parent_overlap = int(
            opts.parent_chunk_overlap
            if opts.parent_chunk_overlap is not None
            else max(overlap, 80)
        )
        meta["parent_chunk_size"] = parent_size
        meta["parent_chunk_overlap"] = parent_overlap
        result = _split_parent_child(raw, size, overlap, parent_size, parent_overlap)
        result.meta = meta
        result.texts = [t.strip() for t in result.texts if t and t.strip()]
        if result.embed_texts is not None:
            # 与 texts 对齐清洗
            paired = [
                (s, e)
                for s, e in zip(result.texts, result.embed_texts)
                if (s or "").strip() and (e or "").strip()
            ]
            result.texts = [p[0] for p in paired]
            result.embed_texts = [p[1] for p in paired]
        return result
    else:
        # recursive（默认）
        chunks = _recursive_splitter(size, overlap).split_text(raw)

    cleaned = [c.strip() for c in chunks if c and c.strip()]
    return SplitResult(texts=cleaned, embed_texts=None, meta=meta)


def split_text(text: str, options: SplitOptions | None = None) -> list[str]:
    """
    同步切分（不含 semantic 异步路径）。
    semantic 在同步接口下回退为 sentence，保持旧调用兼容。
    """
    opts = options or SplitOptions()
    if opts.normalized_strategy() == "semantic":
        logger.info("同步 split_text 不跑语义 Embedding，回退 sentence")
        opts = SplitOptions(
            strategy="sentence",
            chunk_size=opts.chunk_size,
            chunk_overlap=opts.chunk_overlap,
        )
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # 已在事件循环中：仅跑非 async 策略分支
        size = opts.resolved_size()
        overlap = opts.resolved_overlap()
        strategy = opts.normalized_strategy()
        raw = text or ""
        if strategy == "fixed":
            return _split_fixed(raw, size, overlap)
        if strategy == "markdown_header":
            return _split_markdown_header(raw, size, overlap)
        if strategy == "paragraph":
            return _split_paragraph(raw, size, overlap)
        if strategy == "sentence":
            return _split_sentence_chunks(raw, size, overlap)
        if strategy == "parent_child":
            parent_size = int(opts.parent_chunk_size or max(size * 3, 1200))
            parent_overlap = int(
                opts.parent_chunk_overlap
                if opts.parent_chunk_overlap is not None
                else max(overlap, 80)
            )
            return _split_parent_child(
                raw, size, overlap, parent_size, parent_overlap
            ).texts
        return [
            t.strip()
            for t in _recursive_splitter(size, overlap).split_text(raw)
            if t and t.strip()
        ]

    return asyncio.run(split_text_async(text, opts)).texts


def _read_text(file_path: str, filename: str | None = None) -> str:
    """按扩展名提取纯文本（md/txt/pdf/docx/html/csv）。"""
    from app.rag_engine.document_loader import load_document_text

    return load_document_text(file_path, filename=filename)


def split_file(
    file_path: str,
    encoding: str | None = None,
    options: SplitOptions | None = None,
    filename: str | None = None,
) -> list[str]:
    """读取本地文档并切片（同步，兼容旧调用）。"""
    if encoding:
        with open(file_path, "r", encoding=encoding) as f:
            return split_text(f.read(), options)
    return split_text(_read_text(file_path, filename=filename), options)


async def split_file_async(
    file_path: str,
    encoding: str | None = None,
    options: SplitOptions | None = None,
    filename: str | None = None,
) -> SplitResult:
    """异步读文件并切分（支持多格式）。"""
    if encoding:
        with open(file_path, "r", encoding=encoding) as f:
            return await split_text_async(f.read(), options)
    return await split_text_async(
        _read_text(file_path, filename=filename), options
    )
