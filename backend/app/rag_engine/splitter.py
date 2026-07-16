"""文档切片（参数写死在 config：500 / 50）"""

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


def split_file(file_path: str, encoding: str = "utf-8") -> list[str]:
    """读取本地 md/txt 并切片"""
    with open(file_path, "r", encoding=encoding) as f:
        return split_text(f.read())
