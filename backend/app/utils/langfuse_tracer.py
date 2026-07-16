"""
Langfuse 追踪封装（后端 A · V2）
- 未配置 Key / 未安装 SDK 时自动降级为 no-op，不影响主链路
- 兼容 langfuse 经典 trace/span/generation API
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app import config

logger = logging.getLogger(__name__)

_client = None
_init_tried = False


def langfuse_enabled() -> bool:
    return bool(config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_SECRET_KEY)


def get_langfuse():
    """懒加载 Langfuse 客户端；不可用时返回 None"""
    global _client, _init_tried
    if _init_tried:
        return _client
    _init_tried = True
    if not langfuse_enabled():
        logger.info("Langfuse 未配置，跳过追踪上报")
        return None
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
        )
        logger.info("Langfuse 客户端已初始化 host=%s", config.LANGFUSE_HOST)
    except Exception as e:
        logger.warning("Langfuse 初始化失败，降级为本地无追踪: %s", e)
        _client = None
    return _client


def new_request_id() -> str:
    return str(uuid.uuid4())


class NullTrace:
    """无 Langfuse 时的空实现，保证调用方代码一致"""

    id: str | None = None

    def span(self, **kwargs):
        return NullSpan()

    def generation(self, **kwargs):
        return NullGeneration()

    def update(self, **kwargs):
        return self


class NullSpan:
    def end(self, **kwargs):
        return self

    def update(self, **kwargs):
        return self


class NullGeneration:
    def end(self, **kwargs):
        return self

    def update(self, **kwargs):
        return self


def start_trace(
    name: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    input_data: Any = None,
    request_id: str | None = None,
):
    """创建顶层 Trace；失败则返回 NullTrace"""
    rid = request_id or new_request_id()
    client = get_langfuse()
    if client is None:
        t = NullTrace()
        t.id = rid
        return t
    try:
        kwargs: dict[str, Any] = {
            "name": name,
            "id": rid,
            "metadata": {**(metadata or {}), "request_id": rid, "env": config.ENV},
        }
        if user_id:
            kwargs["user_id"] = str(user_id)
        if session_id:
            kwargs["session_id"] = str(session_id)
        if input_data is not None:
            kwargs["input"] = input_data
        trace = client.trace(**kwargs)
        return trace
    except Exception as e:
        logger.warning("创建 Langfuse Trace 失败: %s", e)
        t = NullTrace()
        t.id = rid
        return t


def safe_end(obj, **kwargs) -> None:
    if obj is None:
        return
    try:
        if hasattr(obj, "end"):
            obj.end(**kwargs)
        elif hasattr(obj, "update"):
            obj.update(**kwargs)
    except Exception as e:
        logger.debug("Langfuse end/update 忽略: %s", e)


def flush() -> None:
    client = get_langfuse()
    if client is None:
        return
    try:
        client.flush()
    except Exception as e:
        logger.debug("Langfuse flush 忽略: %s", e)
