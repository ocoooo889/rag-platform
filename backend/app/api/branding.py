import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.db.models import SystemConfig, User
from app.schema.schemas import ResponseModel
from app.utils.auth import get_current_user
from app.utils.permission import is_admin

router = APIRouter(prefix="/api/system", tags=["branding"])

# 存放白标静态文件的物理路径
BRANDING_DIR = "./uploads/branding"

# 默认白标配置项，用于兜底
DEFAULTS = {
    "brand_name": "RAG 智能知识平台",
    "brand_logo_url": "/uploads/branding/logo.png",
    "brand_favicon_url": "/uploads/branding/favicon.ico",
    "brand_theme_color": "#409EFF",
    "brand_login_title": "企业知识，智能问答",
    "brand_footer_text": "Powered by RAG Platform"
}

@router.get("/branding", response_model=ResponseModel)
def get_branding(db: Session = Depends(get_db)):
    """获取系统品牌配置。免鉴权，供登录页和主框架渲染使用。
    若数据库中配置项缺失，则使用默认值兜底并返回 4003。
    """
    configs = db.query(SystemConfig).all()
    config_map = {c.config_key: c.config_value for c in configs}
    
    missing_config = False
    result_data = {}
    
    for key, default_val in DEFAULTS.items():
        if key not in config_map:
            missing_config = True
            result_data[key] = default_val
        else:
            result_data[key] = config_map[key]
            
    if missing_config:
        return ResponseModel(
            code=4003, 
            msg="系统品牌配置未初始化，使用默认值兜底", 
            data=result_data
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新系统品牌配置。需要管理员权限。
    支持表单字段形式提交，并上传 Logo、Favicon 资源文件。
    """
    # 1. 鉴权校验 - 必须是管理员才能修改系统配置
    if not is_admin(current_user):
        return ResponseModel(code=403, msg="权限不足，仅管理员可修改品牌配置")
        
    os.makedirs(BRANDING_DIR, exist_ok=True)
    
    # 2. 保存新 Logo（如果有上传）
    logo_url = DEFAULTS["brand_logo_url"]
    if brand_logo and brand_logo.filename:
        # 获取文件后缀
        ext = os.path.splitext(brand_logo.filename)[1]
        logo_filename = f"logo{ext}"
        logo_path = os.path.join(BRANDING_DIR, logo_filename)
        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(brand_logo.file, buffer)
        logo_url = f"/uploads/branding/{logo_filename}"

    # 3. 保存新 Favicon（如果有上传）
    favicon_url = DEFAULTS["brand_favicon_url"]
    if brand_favicon and brand_favicon.filename:
        ext = os.path.splitext(brand_favicon.filename)[1]
        favicon_filename = f"favicon{ext}"
        favicon_path = os.path.join(BRANDING_DIR, favicon_filename)
        with open(favicon_path, "wb") as buffer:
            shutil.copyfileobj(brand_favicon.file, buffer)
        favicon_url = f"/uploads/branding/{favicon_filename}"

    # 4. 更新数据库配置项
    updates = {
        "brand_name": brand_name,
        "brand_theme_color": brand_theme_color,
        "brand_login_title": brand_login_title,
        "brand_footer_text": brand_footer_text
    }
    
    # 如果上传了新文件，则加入更新字段
    if brand_logo and brand_logo.filename:
        updates["brand_logo_url"] = logo_url
    if brand_favicon and brand_favicon.filename:
        updates["brand_favicon_url"] = favicon_url

    for k, v in updates.items():
        config_item = db.query(SystemConfig).filter(SystemConfig.config_key == k).first()
        if not config_item:
            config_item = SystemConfig(config_key=k, config_value=v)
            db.add(config_item)
        else:
            config_item.config_value = v

    db.commit()
    
    # 5. 重新获取最新配置并返回
    configs = db.query(SystemConfig).all()
    latest_config_map = {c.config_key: c.config_value for c in configs}
    
    # 兜底返回合并后的结果
    return_data = {}
    for key in DEFAULTS.keys():
        return_data[key] = latest_config_map.get(key, DEFAULTS[key])
        
    return ResponseModel(data=return_data)
