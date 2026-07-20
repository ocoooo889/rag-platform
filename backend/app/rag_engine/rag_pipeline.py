"""
RAG 全链路（后端 A · V2）
带 Langfuse Trace：retrieval span + llm generation
未配置 Langfuse 时行为与直接调用 retriever/generator 一致
"""

from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator

from app import config
from app.rag_engine.generator import generate_answer, generate_answer_stream
from app.rag_engine.prompt_guard import sanitize_hits, sanitize_user_query
from app.rag_engine.query_rewrite import rewrite_query_for_retrieve
from app.rag_engine.retriever import retrieve
from app.utils.langfuse_tracer import flush, safe_end, start_trace

logger = logging.getLogger(__name__)


class RAGPipeline:
    """完整 RAG 链路，带 Langfuse 追踪"""

    @staticmethod
    async def retrieve_only(
        *,
        query: str,
        texts: list[str],
        ids: list[str],
        search_type: str,
        top_n: int | None = None,
        kb_id: str | None = None,
        doc_id: str | None = None,
        source_docs: list[str] | None = None,
        doc_ids: list[str] | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        enable_rerank: bool | None = None,
    ) -> tuple[list[dict], dict]:
        """仅检索（命中测试），上报 retrieval Trace"""
        trace = start_trace(
            "rag_retrieve",
            user_id=user_id,
            metadata={
                "kb_id": kb_id,
                "doc_id": doc_id,
                "search_type": search_type,
            },
            input_data={"query": query},
            request_id=request_id,
        )
        span = trace.span(name="retrieval", input={"query": query, "search_type": search_type})
        t0 = time.perf_counter()
        try:
            hits, retrieve_meta = await retrieve(
                query,
                texts,
                ids,
                search_type,
                top_n,
                doc_id=doc_id,
                kb_id=kb_id,
                source_docs=source_docs,
                doc_ids=doc_ids,
                enable_rerank=enable_rerank,
            )
            hits = sanitize_hits(hits)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            safe_end(
                span,
                output={
                    "hits_count": len(hits),
                    "scores": [h.get("score") for h in hits[:5]],
                    "elapsed_ms": elapsed_ms,
                    "retrieve_meta": retrieve_meta,
                },
            )
            try:
                trace.update(
                    output={"hits_count": len(hits), "elapsed_ms": elapsed_ms}
                )
            except Exception:
                pass
            return hits, retrieve_meta
        except Exception as e:
            safe_end(span, output={"error": str(e)})
            raise
        finally:
            flush()

    @staticmethod
    async def query(
        *,
        kb_id: str,
        query: str,
        search_type: str,
        texts: list[str],
        ids: list[str],
        top_n: int | None = None,
        source_docs: list[str] | None = None,
        doc_ids: list[str] | None = None,
        chat_history: str = "",
        user_id: str | None = None,
        session_id: str | None = None,
        stream: bool = False,
        request_id: str | None = None,
        enable_rerank: bool | None = None,
    ) -> tuple[Any, list[dict], dict]:
        """
        完整 RAG：检索 + LLM 生成。
        stream=False 时返回 (answer: str, hits, meta)
        stream=True 时返回 (async_iterator, hits, meta)，调用方自行消费 iterator
        """
        pipeline_meta: dict[str, Any] = {
            "rewritten_query": query,
            "query_rewritten": False,
            "guard_warnings": [],
            "retrieve": {},
        }
        safe_query, guard_warnings = sanitize_user_query(query)
        if guard_warnings:
            pipeline_meta["guard_warnings"] = guard_warnings
        query = safe_query or query
        trace = start_trace(
            "rag_query",
            user_id=user_id,
            session_id=session_id,
            metadata={"kb_id": kb_id, "search_type": search_type},
            input_data={"query": query},
            request_id=request_id,
        )

        # 阶段 0：多轮 Query Rewrite（仅影响检索；生成仍用用户原问）
        # 流式默认跳过改写，避免首 token 前多一轮 LLM
        retrieve_query = query
        do_rewrite = True
        if stream and not bool(getattr(config, "QUERY_REWRITE_ON_STREAM", False)):
            do_rewrite = False
        rewrite_span = trace.span(
            name="query_rewrite",
            input={
                "query": query,
                "has_history": bool((chat_history or "").strip()),
                "skipped": not do_rewrite,
            },
        )
        t_rw = time.perf_counter()
        try:
            if do_rewrite:
                retrieve_query = await rewrite_query_for_retrieve(query, chat_history)
        except Exception as e:
            logger.warning("Query Rewrite 外层异常，使用原句检索: %s", e)
            retrieve_query = query
        rewrite_ms = round((time.perf_counter() - t_rw) * 1000, 2)
        pipeline_meta["rewritten_query"] = retrieve_query
        pipeline_meta["query_rewritten"] = retrieve_query != query
        safe_end(
            rewrite_span,
            output={
                "retrieve_query": retrieve_query,
                "rewritten": retrieve_query != query,
                "elapsed_ms": rewrite_ms,
                "skipped": not do_rewrite,
            },
        )

        # 阶段 1：检索（使用改写后的问句）
        retrieval_span = trace.span(
            name="retrieval",
            input={"query": retrieve_query, "user_query": query},
        )
        t0 = time.perf_counter()
        try:
            hits, retrieve_meta = await retrieve(
                retrieve_query,
                texts,
                ids,
                search_type,
                top_n,
                kb_id=kb_id,
                source_docs=source_docs,
                doc_ids=doc_ids,
                enable_rerank=enable_rerank,
            )
            hits = sanitize_hits(hits)
        except Exception as e:
            logger.warning("RAG 检索失败，降级为空上下文: %s", e)
            hits = []
            retrieve_meta = {"fallback": "empty", "search_type": search_type}
        pipeline_meta["retrieve"] = retrieve_meta
        retrieve_ms = round((time.perf_counter() - t0) * 1000, 2)
        safe_end(
            retrieval_span,
            output={
                "hits_count": len(hits),
                "scores": [h.get("score") for h in hits[:5]],
                "elapsed_ms": retrieve_ms,
                "retrieve_query": retrieve_query,
            },
        )

        # 阶段 2：LLM 生成（始终回答用户原始 query）
        generation = trace.generation(
            name="llm_response",
            model=config.LLM_MODEL,
            input={
                "query": query,
                "retrieve_query": retrieve_query,
                "context": hits,
                "chat_history": chat_history or "（无历史）",
            },
        )

        if stream:
            async def _gen() -> AsyncIterator[str]:
                full = ""
                t1 = time.perf_counter()
                try:
                    async for token in generate_answer_stream(hits, query, chat_history):
                        full += token
                        yield token
                finally:
                    llm_ms = round((time.perf_counter() - t1) * 1000, 2)
                    safe_end(
                        generation,
                        output=full,
                        metadata={"elapsed_ms": llm_ms, "stream": True},
                    )
                    try:
                        trace.update(
                            output={
                                "answer_preview": full[:200],
                                "hits_count": len(hits),
                                "retrieve_ms": retrieve_ms,
                                "llm_ms": llm_ms,
                            }
                        )
                    except Exception:
                        pass
                    flush()

            return _gen(), hits, pipeline_meta

        t1 = time.perf_counter()
        answer = await generate_answer(hits, query, chat_history)
        llm_ms = round((time.perf_counter() - t1) * 1000, 2)
        safe_end(
            generation,
            output=answer,
            metadata={"elapsed_ms": llm_ms, "stream": False},
        )
        try:
            trace.update(
                output={
                    "answer_preview": (answer or "")[:200],
                    "hits_count": len(hits),
                    "retrieve_ms": retrieve_ms,
                    "llm_ms": llm_ms,
                }
            )
        except Exception:
            pass
        flush()
        return answer, hits, pipeline_meta
