import os
import sys
import json
from loguru import logger
from contextvars import ContextVar
from datetime import datetime

# 用 ContextVar 存储线程/协程隔离的请求上下文
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[int] = ContextVar("user_id", default=0)
action_var: ContextVar[str] = ContextVar("action", default="-")

def json_formatter(record):
    """自定义日志序列化器，用于输出结构化 JSON"""
    extra = record["extra"]
    log_record = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
        "level": record["level"].name,
        "request_id": extra.get("request_id", "-"),
        "user_id": extra.get("user_id", 0),
        "action": extra.get("action", "-"),
        "kb_id": extra.get("kb_id", None),
        "doc_id": extra.get("doc_id", None),
        "search_type": extra.get("search_type", None),
        "query": extra.get("query", None),
        "duration_ms": extra.get("duration_ms", None),
        "message": record["message"]
    }
    # 仅序列化不为 None 的字段
    filtered_record = {k: v for k, v in log_record.items() if v is not None}
    record["extra"]["serialized"] = json.dumps(filtered_record, ensure_ascii=False)
    return "{extra[serialized]}\n"

def setup_logger():
    """初始化结构化日志"""
    log_dir = os.getenv("LOG_DIR", "./logs")
    os.makedirs(log_dir, exist_ok=True)

    # 每次打日志时，动态注入 ContextVar 中的 request_id, user_id, action
    def patch_record(record):
        record["extra"].setdefault("request_id", request_id_var.get())
        record["extra"].setdefault("user_id", user_id_var.get())
        record["extra"].setdefault("action", action_var.get())

    logger.remove()
    
    # 应用 patch 处理器
    patched_logger = logger.patch(patch_record)
    
    # 控制台输出 JSON 格式日志 (INFO 及以上)
    patched_logger.add(
        sys.stdout,
        format=json_formatter,
        level="INFO"
    )
    
    # 文件输出 JSON 格式日志 (DEBUG 及以上，按天轮转)
    patched_logger.add(
        f"{log_dir}/rag_{{time:YYYY-MM-DD}}.log",
        format=json_formatter,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8"
    )
    return patched_logger

# 实例化全局 logger
logger = setup_logger()
