"""Chroma 向量写入 / 查询 / 删除（按 kb_id、doc_id 隔离）"""

from __future__ import annotations

import asyncio
import logging
import os
import urllib.request

import chromadb

from app import config
from app.utils.llm_client import get_embedding, get_embeddings_batch

logger = logging.getLogger(__name__)

# 本机地址：系统代理（如小茅）拦截 HttpClient 时会导致向量写入永久挂起
_LOCAL_NO_PROXY = ("127.0.0.1", "localhost", "::1")


class VectorStoreError(Exception):
    """Chroma / 向量库不可用（与 Embedding API 失败区分）"""

    def __init__(self, message: str = "向量库暂不可用，已切换关键词检索"):
        self.message = message
        super().__init__(message)


def _ensure_local_no_proxy() -> None:
    """确保访问本机 Chroma 时不走系统/环境代理。"""
    for key in ("NO_PROXY", "no_proxy"):
        cur = [x.strip() for x in (os.environ.get(key) or "").split(",") if x.strip()]
        merged = list(dict.fromkeys([*cur, *_LOCAL_NO_PROXY]))
        os.environ[key] = ",".join(merged)


def _chroma_host_candidates() -> list[str]:
    """Windows 上 localhost 常走 ::1，而 127.0.0.1 可能未监听，需双向回退。"""
    primary = (config.CHROMA_HOST or "localhost").strip() or "localhost"
    # 优先 127.0.0.1，减少 localhost→::1 撞上 Docker/WSL 占用端口
    alts = ["127.0.0.1", "localhost"]
    out: list[str] = []
    for h in [primary, *alts]:
        if h and h not in out:
            out.append(h)
    return out


def probe_chroma_heartbeat(timeout: float = 2.5) -> tuple[bool, str, str]:
    """
    HTTP 探测 /api/v2/heartbeat。
    返回 (ok, detail, resolved_host)。
    """
    _ensure_local_no_proxy()
    port = config.CHROMA_PORT
    last_err = "连接失败"
    # 直连、不走代理（urllib 默认可能读系统代理）
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    for host in _chroma_host_candidates():
        url = f"http://{host}:{port}/api/v2/heartbeat"
        try:
            with opener.open(url, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    return True, f"{host}:{port}", host
        except Exception as e:  # noqa: BLE001
            last_err = str(e)[:120] or "连接失败"
    return False, last_err, config.CHROMA_HOST


def get_chroma_client():
    """获取可用的 HttpClient；优先 .env，失败则回退 localhost/127.0.0.1。"""
    _ensure_local_no_proxy()
    port = config.CHROMA_PORT
    last_err: Exception | None = None
    # 先用廉价 heartbeat 选定可达 host，再建 client（避免 chromadb 空 ValueError）
    ok, detail, host = probe_chroma_heartbeat()
    if ok:
        try:
            return chromadb.HttpClient(host=host, port=port)
        except Exception as e:
            last_err = e
            logger.warning("Chroma HttpClient(%s) 失败: %s", host, e)

    for host in _chroma_host_candidates():
        try:
            client = chromadb.HttpClient(host=host, port=port)
            client.heartbeat()
            return client
        except Exception as e:
            last_err = e
            logger.warning("连接 Chroma 失败 %s:%s — %s", host, port, e)

    raise VectorStoreError(
        f"向量库（Chroma {config.CHROMA_HOST}:{port}）未启动或地址不通（{detail if not ok else last_err}），已切换关键词检索"
    ) from last_err


def _get_collection():
    try:
        client = get_chroma_client()
        return client.get_or_create_collection(name=config.CHROMA_COLLECTION_NAME)
    except VectorStoreError:
        raise
    except Exception as e:
        logger.warning(
            "连接 Chroma 失败 %s:%s — %s",
            config.CHROMA_HOST,
            config.CHROMA_PORT,
            e,
        )
        raise VectorStoreError(
            f"向量库（Chroma {config.CHROMA_HOST}:{config.CHROMA_PORT}）未启动，已切换关键词检索"
        ) from e


def _distance_to_score(distance) -> float:
    """Chroma 距离 → 0~1 相似度"""
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return 0.0
    return round(1.0 / (1.0 + max(d, 0.0)), 4)


def _chroma_add_sync(
    texts: list[str],
    ids: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict] | None,
) -> None:
    """同步写 Chroma（供 to_thread，避免堵死 asyncio 事件循环）"""
    collection = _get_collection()
    kwargs = {"embeddings": embeddings, "documents": texts, "ids": ids}
    if metadatas:
        kwargs["metadatas"] = metadatas
    collection.add(**kwargs)


def _chroma_query_sync(query_vec: list[float], n_results: int, where: dict | None) -> dict:
    collection = _get_collection()
    kwargs = {
        "query_embeddings": [query_vec],
        "n_results": n_results,
        "include": ["documents", "distances", "metadatas"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def _chroma_delete_sync(ids: list[str]) -> None:
    collection = _get_collection()
    collection.delete(ids=ids)


async def embed_and_store(
    texts: list[str],
    ids: list[str],
    metadatas: list[dict] | None = None,
) -> None:
    # 分批：降低单次 Embedding/写入耗时，并在批次间让出事件循环
    batch = max(1, int(getattr(config, "EMBEDDING_BATCH_SIZE", 10) or 10))
    total = 0
    for start in range(0, len(texts), batch):
        end = start + batch
        part_texts = texts[start:end]
        part_ids = ids[start:end]
        part_meta = metadatas[start:end] if metadatas else None
        embeddings = await get_embeddings_batch(part_texts)
        try:
            await asyncio.to_thread(
                _chroma_add_sync, part_texts, part_ids, embeddings, part_meta
            )
        except VectorStoreError:
            raise
        except Exception as e:
            logger.warning("写入 Chroma 失败: %s", e)
            raise VectorStoreError("向量库写入失败，已切换关键词检索") from e
        total += len(part_texts)
        await asyncio.sleep(0)
    logger.info("写入 Chroma %s 条，集合=%s", total, config.CHROMA_COLLECTION_NAME)


async def query_similar(
    query: str,
    top_n: int = 3,
    where: dict | None = None,
) -> list[dict]:
    query_vec = await get_embedding(query)
    n_results = max(top_n, 1)
    try:
        results = await asyncio.to_thread(_chroma_query_sync, query_vec, n_results, where)
    except VectorStoreError:
        raise
    except Exception as e:
        logger.warning("Chroma 查询失败: %s", e)
        raise VectorStoreError("向量库查询失败，已切换关键词检索") from e

    hits = []
    if not results.get("ids") or not results["ids"][0]:
        return hits

    for i, cid in enumerate(results["ids"][0]):
        meta = {}
        if results.get("metadatas") and results["metadatas"][0]:
            meta = results["metadatas"][0][i] or {}
        dist = None
        if results.get("distances") and results["distances"][0]:
            dist = results["distances"][0][i]
        hits.append({
            "chunk_id": cid,
            "content": results["documents"][0][i] if results.get("documents") else "",
            "score": _distance_to_score(dist),
            "source_doc": meta.get("source_doc", "") or "",
            "doc_id": meta.get("doc_id", "") or "",
        })
    return hits


async def delete_from_chroma(ids: list[str]) -> None:
    if not ids:
        return
    try:
        await asyncio.to_thread(_chroma_delete_sync, ids)
    except Exception as e:
        logger.warning("Chroma 删除忽略: %s", e)
