"""文档切片（默认 500/50，可用 .env CHUNK_SIZE / CHUNK_OVERLAP 调整）"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app import config


def split_text(text: str) -> list[str]:
    """把纯文本切成片段列表"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=config.SEPARATORS,
        length_function=len,
    )
    return [t.strip() for t in splitter.split_text(text) if t.strip()]


def _read_text(file_path: str) -> str:
    """UTF-8 优先，失败再试 utf-8-sig / gbk（Windows 长文档常见）。"""
    last_err: Exception | None = None
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise ValueError(f"无法解码文档，已尝试 utf-8/gbk：{last_err}")


def split_file(file_path: str, encoding: str | None = None) -> list[str]:
    """读取本地 md/txt 并切片"""
    if encoding:
        with open(file_path, "r", encoding=encoding) as f:
            return split_text(f.read())
    return split_text(_read_text(file_path))
