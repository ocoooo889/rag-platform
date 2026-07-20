import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import config
from app.db.database import get_db
from app.db.models import LLMConfig, SystemConfig, User
from app.schema.request_schema import (
    LLMConfigCreate,
    LLMConfigUpdate,
    RuntimeModelConfigUpdate,
)
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user
from app.utils.logger import logger
from app.utils.permission import ensure_admin_or_response

router = APIRouter(prefix="/api/models", tags=["models"])
runtime_router = APIRouter(prefix="/api/runtime-config", tags=["runtime-config"])

_RUNTIME_CONFIG_KEY = "runtime_model_config"

# 参数区间由后端下发，前端不得硬编码（addv2）
_PARAMETER_LIMITS: dict[str, Any] = {
    "chat": {
        "temperature": {
            "label": "温度",
            "type": "float",
            "min": 0.0,
            "max": 2.0,
            "default": 0.7,
            "step": 0.1,
        },
        "top_p": {
            "label": "Top P",
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "default": 1.0,
            "step": 0.05,
        },
        "max_tokens": {
            "label": "最大输出 Token",
            "type": "int",
            "min": 1,
            "max": 8192,
            "default": 2048,
            "step": 1,
        },
        "presence_penalty": {
            "label": "存在惩罚",
            "type": "float",
            "min": -2.0,
            "max": 2.0,
            "default": 0.0,
            "step": 0.1,
        },
        "frequency_penalty": {
            "label": "频率惩罚",
            "type": "float",
            "min": -2.0,
            "max": 2.0,
            "default": 0.0,
            "step": 0.1,
        },
    },
    "embedding": {
        "dimension": {
            "label": "向量维度",
            "type": "enum",
            "options": [384, 768, 1024, 1536],
            "default": config.EMBEDDING_DIM,
        },
    },
}


def _normalize_model_type(raw: str | None) -> str:
    text = (raw or "").strip().lower()
    if text in {"llm", "chat"}:
        return "chat"
    if text == "embedding":
        return "embedding"
    return text or "chat"


def model_to_dict(model: LLMConfig) -> dict[str, Any]:
    return {
        "id": model.id,
        "model_type": _normalize_model_type(model.model_type),
        "model_name": model.model_name,
        "api_base_url": model.api_base_url,
        "dimension": model.dimension,
        "is_active": model.is_active,
    }


def _default_chat_params() -> dict[str, Any]:
    limits = _PARAMETER_LIMITS["chat"]
    return {key: spec["default"] for key, spec in limits.items()}


def _default_embedding_params() -> dict[str, Any]:
    limits = _PARAMETER_LIMITS["embedding"]
    return {key: spec["default"] for key, spec in limits.items()}


def _default_runtime_selection() -> dict[str, Any]:
    return {
        "chat_model_id": None,
        "embedding_model_id": None,
        "chat_params": _default_chat_params(),
        "embedding_params": _default_embedding_params(),
        "updated_at": None,
    }


def _load_runtime_selection(db: Session) -> dict[str, Any]:
    base = _default_runtime_selection()
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.config_key == _RUNTIME_CONFIG_KEY)
        .first()
    )
    if not row or not row.config_value:
        return base
    try:
        data = json.loads(row.config_value)
    except json.JSONDecodeError:
        logger.warning("runtime_model_config JSON 损坏，使用默认值")
        return base
    if not isinstance(data, dict):
        return base

    for key in ("chat_model_id", "embedding_model_id", "updated_at"):
        if key in data:
            base[key] = data[key]

    chat_params = data.get("chat_params")
    if isinstance(chat_params, dict):
        base["chat_params"] = {**base["chat_params"], **chat_params}

    embedding_params = data.get("embedding_params")
    if isinstance(embedding_params, dict):
        base["embedding_params"] = {**base["embedding_params"], **embedding_params}

    return base


def _save_runtime_selection(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = json.dumps(payload, ensure_ascii=False)
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.config_key == _RUNTIME_CONFIG_KEY)
        .first()
    )
    if row:
        row.config_value = text
    else:
        db.add(SystemConfig(config_key=_RUNTIME_CONFIG_KEY, config_value=text))
    db.commit()
    return payload


def _catalog_models(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(LLMConfig)
        .filter(LLMConfig.is_active.is_(True))
        .order_by(LLMConfig.id.asc())
        .all()
    )
    models = [model_to_dict(row) for row in rows]

    has_chat = any(m["model_type"] == "chat" for m in models)
    has_embedding = any(m["model_type"] == "embedding" for m in models)

    if not has_chat:
        models.append(
            {
                "id": None,
                "model_type": "chat",
                "model_name": config.LLM_MODEL,
                "api_base_url": config.OPENAI_BASE_URL,
                "dimension": None,
                "is_active": True,
                "source": "env",
            }
        )
    if not has_embedding:
        models.append(
            {
                "id": None,
                "model_type": "embedding",
                "model_name": config.EMBEDDING_MODEL,
                "api_base_url": config.OPENAI_BASE_URL,
                "dimension": config.EMBEDDING_DIM,
                "is_active": True,
                "source": "env",
            }
        )
    return models


def _resolve_default_model_ids(
    db: Session, selection: dict[str, Any]
) -> dict[str, Any]:
    if selection.get("chat_model_id") is not None:
        return selection

    chat = (
        db.query(LLMConfig)
        .filter(LLMConfig.is_active.is_(True))
        .filter(LLMConfig.model_type.in_(["chat", "llm"]))
        .order_by(LLMConfig.id.asc())
        .first()
    )
    embedding = (
        db.query(LLMConfig)
        .filter(LLMConfig.is_active.is_(True))
        .filter(LLMConfig.model_type == "embedding")
        .order_by(LLMConfig.id.asc())
        .first()
    )
    if chat:
        selection["chat_model_id"] = chat.id
    if embedding:
        selection["embedding_model_id"] = embedding.id
    return selection


def _validate_chat_params(params: dict[str, Any]) -> dict[str, Any] | str:
    limits = _PARAMETER_LIMITS["chat"]
    validated: dict[str, Any] = {}
    for key, spec in limits.items():
        if key not in params or params[key] is None:
            validated[key] = spec["default"]
            continue
        try:
            if spec["type"] == "int":
                num = int(params[key])
            else:
                num = float(params[key])
        except (TypeError, ValueError):
            return f"{key} 须为数值"
        if num < spec["min"] or num > spec["max"]:
            return f"{key} 须在 {spec['min']}~{spec['max']} 之间"
        validated[key] = int(num) if spec["type"] == "int" else round(num, 4)
    return validated


def _validate_embedding_params(params: dict[str, Any]) -> dict[str, Any] | str:
    spec = _PARAMETER_LIMITS["embedding"]["dimension"]
    value = params.get("dimension", spec["default"])
    try:
        dim = int(value)
    except (TypeError, ValueError):
        return "dimension 须为整数"
    if dim not in spec["options"]:
        return f"dimension 须为 {spec['options']} 之一"
    return {"dimension": dim}


def _build_runtime_payload(db: Session) -> dict[str, Any]:
    models = _catalog_models(db)
    selection = _resolve_default_model_ids(db, _load_runtime_selection(db))
    return {
        "models": models,
        "parameter_limits": _PARAMETER_LIMITS,
        "selection": selection,
    }


@router.post("", response_model=ResponseModel)
def create_model_config(
    cfg: LLMConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    new_model = LLMConfig(
        model_type=_normalize_model_type(cfg.model_type),
        model_name=cfg.model_name,
        api_base_url=cfg.api_base_url,
        dimension=cfg.dimension,
        is_active=cfg.is_active,
    )
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    return ResponseModel(data=model_to_dict(new_model))


@router.get("", response_model=ResponseModel)
def get_model_configs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    configs = db.query(LLMConfig).all()
    return ResponseModel(data=[model_to_dict(c) for c in configs])


@router.put("/{config_id}", response_model=ResponseModel)
def update_model_config(
    config_id: int,
    cfg: LLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not db_config:
        return ResponseModel(code=404, msg="模型配置不存在")

    if cfg.model_type is not None:
        db_config.model_type = _normalize_model_type(cfg.model_type)
    if cfg.model_name is not None:
        db_config.model_name = cfg.model_name
    if cfg.api_base_url is not None:
        db_config.api_base_url = cfg.api_base_url
    if cfg.dimension is not None:
        db_config.dimension = cfg.dimension
    if cfg.is_active is not None:
        db_config.is_active = cfg.is_active

    db.commit()
    db.refresh(db_config)
    return ResponseModel(data=model_to_dict(db_config))


@router.delete("/{config_id}", response_model=ResponseModel)
def delete_model_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    db_config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not db_config:
        return ResponseModel(code=404, msg="模型配置不存在")

    db.delete(db_config)
    db.commit()
    return ResponseModel(msg="模型配置删除成功")


@runtime_router.get("/models", response_model=ResponseModel)
def get_runtime_model_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    大模型运行配置：下发模型列表 + 参数区间 + 当前选中项。
    前端不得硬编码模型名与上下限（addv2）。
    """
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied
    return ResponseModel(data=_build_runtime_payload(db))


@runtime_router.put("/models", response_model=ResponseModel)
def save_runtime_model_config(
    body: RuntimeModelConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存大模型运行配置（选中模型 + 参数值）。"""
    denied = ensure_admin_or_response(current_user)
    if denied:
        return denied

    current = _resolve_default_model_ids(db, _load_runtime_selection(db))
    chat_model_id = (
        body.chat_model_id
        if body.chat_model_id is not None
        else current.get("chat_model_id")
    )
    embedding_model_id = (
        body.embedding_model_id
        if body.embedding_model_id is not None
        else current.get("embedding_model_id")
    )

    if chat_model_id is not None:
        chat_row = db.query(LLMConfig).filter(LLMConfig.id == chat_model_id).first()
        if not chat_row:
            return ResponseModel(code=404, msg="聊天模型不存在")
        if _normalize_model_type(chat_row.model_type) != "chat":
            return ResponseModel(code=400, msg="chat_model_id 须指向聊天模型")

    if embedding_model_id is not None:
        emb_row = (
            db.query(LLMConfig).filter(LLMConfig.id == embedding_model_id).first()
        )
        if not emb_row:
            return ResponseModel(code=404, msg="嵌入模型不存在")
        if _normalize_model_type(emb_row.model_type) != "embedding":
            return ResponseModel(code=400, msg="embedding_model_id 须指向嵌入模型")

    chat_params = dict(current.get("chat_params") or _default_chat_params())
    if body.chat_params is not None:
        chat_params.update(body.chat_params.model_dump(exclude_unset=True))
    validated_chat = _validate_chat_params(chat_params)
    if isinstance(validated_chat, str):
        return ResponseModel(code=400, msg=validated_chat)

    embedding_params = dict(
        current.get("embedding_params") or _default_embedding_params()
    )
    if body.embedding_params is not None:
        embedding_params.update(body.embedding_params.model_dump(exclude_unset=True))
    validated_embedding = _validate_embedding_params(embedding_params)
    if isinstance(validated_embedding, str):
        return ResponseModel(code=400, msg=validated_embedding)

    saved = _save_runtime_selection(
        db,
        {
            "chat_model_id": chat_model_id,
            "embedding_model_id": embedding_model_id,
            "chat_params": validated_chat,
            "embedding_params": validated_embedding,
        },
    )
    logger.info("保存 runtime-config/models chat_model_id=%s", chat_model_id)
    return ResponseModel(
        data={
            "models": _catalog_models(db),
            "parameter_limits": _PARAMETER_LIMITS,
            "selection": saved,
        }
    )
