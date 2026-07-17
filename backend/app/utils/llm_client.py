"""
LLM / Embedding 统一封装（3号）
- 超时、重试、降级文案按管控方案
- 兼容百炼 DashScope（text-embedding-v4 + dimensions）
- V2：可选 Langfuse Trace（未配置 Key 时不上报）
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI

from app import config
from app.utils.langfuse_tracer import flush, safe_end, start_trace

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    api_key=config.OPENAI_API_KEY or "sk-missing",
    base_url=config.OPENAI_BASE_URL,
)


class EmbeddingServiceError(Exception):
    """Embedding 不可用，上层应降级为全文检索"""


class LLMServiceError(Exception):
    """大模型不可用；上层应返回 5002，勿用字符串前缀猜测"""

    def __init__(self, message: str = "大模型服务暂时不可用，请稍后重试"):
        self.message = message
        super().__init__(message)


def _is_dashscope() -> bool:
    return "dashscope" in (config.OPENAI_BASE_URL or "").lower()


def _report_generation(
    name: str,
    *,
    model: str,
    input_data: Any,
    output_data: Any = None,
    usage: dict | None = None,
    metadata: dict | None = None,
    trace_id: str | None = None,
) -> None:
    """单次 Embedding/LLM 调用上报（独立短 Trace，便于与 pipeline 互补）"""
    try:
        trace = start_trace(name, metadata=metadata, input_data=input_data, request_id=trace_id)
        gen = trace.generation(
            name=name,
            model=model,
            input=input_data,
            metadata=metadata or {},
        )
        end_kwargs: dict[str, Any] = {}
        if output_data is not None:
            end_kwargs["output"] = output_data
        if usage:
            end_kwargs["usage"] = usage
        safe_end(gen, **end_kwargs)
        flush()
    except Exception as e:
        logger.debug("Langfuse generation 上报忽略: %s", e)


async def get_embedding(text: str) -> list[float]:
    """单条文本向量化"""
    vectors = await get_embeddings_batch([text])
    return vectors[0]


async def get_embeddings_batch(texts: list[str], trace_id: str | None = None) -> list[list[float]]:
    """批量向量化；百炼兼容接口建议每批不超过 10 条"""
    if not texts:
        return []
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("sk-xxxx"):
        raise EmbeddingServiceError("向量模型暂不可用，已切换关键词检索")

    batch_size = max(1, config.EMBEDDING_BATCH_SIZE)
    all_vectors: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        chunk = texts[start:start + batch_size]
        all_vectors.extend(await _embed_one_batch(chunk, trace_id=trace_id))
    return all_vectors


async def _embed_one_batch(texts: list[str], trace_id: str | None = None) -> list[list[float]]:
    last_err: Exception | None = None
    kwargs = {
        "model": config.EMBEDDING_MODEL,
        "input": texts,
    }
    # 百炼 v3/v4 可指定维度，对齐项目 1536
    if _is_dashscope() or str(config.EMBEDDING_MODEL).startswith("text-embedding-v"):
        kwargs["dimensions"] = config.EMBEDDING_DIM

    for attempt in range(config.LLM_MAX_RETRIES + 1):
        try:
            resp = await asyncio.wait_for(
                _client.embeddings.create(**kwargs),
                timeout=config.EMBEDDING_TIMEOUT,
            )
            vectors = [item.embedding for item in resp.data]
            _report_generation(
                "embedding",
                model=config.EMBEDDING_MODEL,
                input_data={"count": len(texts)},
                output_data={"dim": len(vectors[0]) if vectors else 0, "count": len(vectors)},
                metadata={"count": len(texts), "dim": len(vectors[0]) if vectors else 0},
                trace_id=trace_id,
            )
            return vectors
        except Exception as e:
            last_err = e
            logger.warning("Embedding 第 %s 次失败: %s", attempt + 1, e)
            if attempt < config.LLM_MAX_RETRIES:
                await asyncio.sleep(1)
    raise EmbeddingServiceError("向量模型暂不可用，已切换关键词检索") from last_err


async def chat_completion(
    messages: list[dict],
    *,
    query: str = "",
    context: str = "",
    trace_id: str | None = None,
) -> str:
    """非流式对话；失败抛 LLMServiceError（由接口层转 5002）"""
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("sk-xxxx"):
        raise LLMServiceError("大模型服务暂时不可用，请稍后重试")

    last_err: Exception | None = None
    for attempt in range(config.LLM_MAX_RETRIES + 1):
        try:
            resp = await asyncio.wait_for(
                _client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=messages,
                    temperature=0.3,
                ),
                timeout=config.LLM_TIMEOUT,
            )
            content = resp.choices[0].message.content or ""
            usage = None
            if getattr(resp, "usage", None):
                usage = {
                    "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                    "total_tokens": getattr(resp.usage, "total_tokens", None),
                }
            # 若上层已用 rag_pipeline 打 generation，这里仅在有 query 透传时补报
            if query or context:
                _report_generation(
                    "llm_chat",
                    model=config.LLM_MODEL,
                    input_data={"query": query, "context": context},
                    output_data=content,
                    usage=usage,
                    trace_id=trace_id,
                )
            return content
        except Exception as e:
            last_err = e
            logger.warning("LLM 第 %s 次失败: %s", attempt + 1, e)
            if attempt < config.LLM_MAX_RETRIES:
                await asyncio.sleep(1)
    raise LLMServiceError("大模型服务暂时不可用，请稍后重试") from last_err


async def chat_completion_stream(messages: list[dict]):
    """流式对话，逐块 yield 文本；启动失败抛 LLMServiceError"""
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("sk-xxxx"):
        raise LLMServiceError("大模型服务暂时不可用，请稍后重试")

    try:
        stream = await asyncio.wait_for(
            _client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=0.3,
                stream=True,
            ),
            timeout=config.LLM_TIMEOUT,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
    except LLMServiceError:
        raise
    except Exception as e:
        logger.error("LLM 流式失败: %s", e)
        raise LLMServiceError("大模型服务暂时不可用，请稍后重试") from e
