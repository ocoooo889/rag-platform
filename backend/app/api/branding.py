import json
import os
import shutil
import time
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.database import get_db
from app.db.models import SystemConfig, User
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user
from app.utils.permission import is_admin

router = APIRouter(prefix="/api/system", tags=["branding"])

BRANDING_DIR = "./uploads/branding"
LOGO_HISTORY_MAX = 3

DEFAULTS = {
    "brand_name": "RAG 智能知识平台",
    "brand_logo_url": "/uploads/branding/logo.png",
    "brand_favicon_url": "/uploads/branding/favicon.ico",
    "brand_theme_color": "#409EFF",
    "brand_login_title": "企业知识，智能问答",
    "brand_footer_text": "Powered by RAG Platform",
    "brand_logo_history": "[]",
}


def _upsert_config(db: Session, key: str, value: str) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if not row:
        db.add(SystemConfig(config_key=key, config_value=value))
    else:
        row.config_value = value


def _path_key(url: str) -> str:
    return str(url or "").split("?", 1)[0]


def _parse_history(raw) -> List[str]:
    if isinstance(raw, list):
        return [u for u in raw if isinstance(u, str) and u.strip()][:LOGO_HISTORY_MAX]
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [u for u in data if isinstance(u, str) and u.strip()][:LOGO_HISTORY_MAX]
    except Exception:
        pass
    return []


def _history_from_db(db: Session) -> List[str]:
    row = db.query(SystemConfig).filter(SystemConfig.config_key == "brand_logo_history").first()
    return _parse_history(row.config_value if row else "[]")


def _push_logo_history(history: List[str], logo_url: str) -> List[str]:
    key = _path_key(logo_url)
    next_hist = [logo_url] + [u for u in history if _path_key(u) != key]
    return next_hist[:LOGO_HISTORY_MAX]


def _prune_history_files(history: List[str]) -> None:
    """删除 branding 目录中不在历史列表内的 logo_*.png（保留 logo.png）"""
    keep = {_path_key(u).rsplit("/", 1)[-1] for u in history}
    keep.add("logo.png")
    if not os.path.isdir(BRANDING_DIR):
        return
    for name in os.listdir(BRANDING_DIR):
        if not name.startswith("logo_") or not name.endswith(".png"):
            continue
        if name not in keep:
            try:
                os.remove(os.path.join(BRANDING_DIR, name))
            except OSError:
                pass


def _build_payload(config_map: dict) -> dict:
    data = {}
    for key, default_val in DEFAULTS.items():
        if key == "brand_logo_history":
            continue
        data[key] = config_map.get(key, default_val)
    data["brand_logo_history"] = _parse_history(config_map.get("brand_logo_history", "[]"))
    return data


@router.get("/branding", response_model=ResponseModel)
def get_branding(db: Session = Depends(get_db)):
    """获取系统品牌配置。免鉴权，供登录页和主框架渲染使用。"""
    configs = db.query(SystemConfig).all()
    config_map = {c.config_key: c.config_value for c in configs}

    missing_config = False
    for key in DEFAULTS.keys():
        if key not in config_map:
            missing_config = True
            break

    result_data = _build_payload(config_map)

    if missing_config:
        return ResponseModel(
            code=4003,
            msg="系统品牌配置未初始化，使用默认值兜底",
            data=result_data,
        )

    return ResponseModel(code=0, msg="success", data=result_data)


@router.put("/branding", response_model=ResponseModel)
async def update_branding(
    brand_name: str = Form(...),
    brand_theme_color: str = Form(...),
    brand_login_title: str = Form(...),
    brand_footer_text: str = Form(...),
    brand_logo: Optional[UploadFile] = File(None),
    brand_favicon: Optional[UploadFile] = File(None),
    brand_logo_history_pick: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新系统品牌配置。需要管理员权限。支持上传 Logo / 回选历史 Logo。"""
    if not is_admin(current_user):
        return ResponseModel(code=403, msg="权限不足，仅管理员可修改品牌配置")

    brand_name = (brand_name or "").strip()
    if not brand_name:
        return ResponseModel(code=400, msg="系统名称不能为空")
    if len(brand_name) > 10:
        return ResponseModel(code=400, msg="系统名称最多10个字")

    os.makedirs(BRANDING_DIR, exist_ok=True)
    history = _history_from_db(db)
    updates = {
        "brand_name": brand_name,
        "brand_theme_color": brand_theme_color,
        "brand_login_title": brand_login_title,
        "brand_footer_text": brand_footer_text,
    }

    # 优先：新上传 Logo → 写入历史文件并置为当前
    if brand_logo and brand_logo.filename:
        ts = int(time.time())
        logo_filename = f"logo_{ts}.png"
        logo_path = os.path.join(BRANDING_DIR, logo_filename)
        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(brand_logo.file, buffer)
        # 同步一份到 logo.png，兼容旧默认路径
        shutil.copyfile(logo_path, os.path.join(BRANDING_DIR, "logo.png"))
        logo_url = f"/uploads/branding/{logo_filename}?v={ts}"
        history = _push_logo_history(history, logo_url)
        _prune_history_files(history)
        updates["brand_logo_url"] = logo_url
        updates["brand_logo_history"] = json.dumps(history, ensure_ascii=False)

    # 次选：从历史回选（无新上传时）
    elif brand_logo_history_pick:
        pick = brand_logo_history_pick.strip()
        pick_key = _path_key(pick)
        matched = next((u for u in history if _path_key(u) == pick_key), None)
        if not matched:
            return ResponseModel(code=400, msg="历史 Logo 不存在或已失效")
        abs_path = os.path.join(BRANDING_DIR, pick_key.rsplit("/", 1)[-1])
        if not os.path.isfile(abs_path):
            return ResponseModel(code=400, msg="历史 Logo 文件缺失")
        ts = int(time.time())
        logo_url = f"{pick_key}?v={ts}"
        shutil.copyfile(abs_path, os.path.join(BRANDING_DIR, "logo.png"))
        history = _push_logo_history(history, logo_url)
        updates["brand_logo_url"] = logo_url
        updates["brand_logo_history"] = json.dumps(history, ensure_ascii=False)

    if brand_favicon and brand_favicon.filename:
        ext = os.path.splitext(brand_favicon.filename)[1] or ".ico"
        favicon_filename = f"favicon{ext}"
        favicon_path = os.path.join(BRANDING_DIR, favicon_filename)
        with open(favicon_path, "wb") as buffer:
            shutil.copyfileobj(brand_favicon.file, buffer)
        updates["brand_favicon_url"] = f"/uploads/branding/{favicon_filename}?v={int(time.time())}"

    for k, v in updates.items():
        _upsert_config(db, k, v)

    db.commit()

    configs = db.query(SystemConfig).all()
    latest_config_map = {c.config_key: c.config_value for c in configs}
    return ResponseModel(data=_build_payload(latest_config_map))
