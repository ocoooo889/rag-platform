from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import LLMConfig, User
from app.schema.request_schema import LLMConfigCreate, LLMConfigUpdate
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/models", tags=["models"])

def model_to_dict(model: LLMConfig):
    return {
        "id": model.id,
        "model_type": model.model_type,
        "model_name": model.model_name,
        "api_base_url": model.api_base_url,
        "dimension": model.dimension,
        "is_active": model.is_active
    }

@router.post("", response_model=ResponseModel)
def create_model_config(
    config: LLMConfigCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """创建新的大模型或 Embedding 模型配置"""
    new_model = LLMConfig(
        model_type=config.model_type,
        model_name=config.model_name,
        api_base_url=config.api_base_url,
        dimension=config.dimension,
        is_active=config.is_active
    )
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    return ResponseModel(data=model_to_dict(new_model))

@router.get("", response_model=ResponseModel)
def get_model_configs(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """获取所有模型配置列表"""
    configs = db.query(LLMConfig).all()
    return ResponseModel(data=[model_to_dict(c) for c in configs])

@router.put("/{config_id}", response_model=ResponseModel)
def update_model_config(
    config_id: int, 
    config: LLMConfigUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """修改指定模型配置"""
    db_config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not db_config:
        return ResponseModel(code=404, msg="模型配置不存在")
    
    if config.model_type is not None:
        db_config.model_type = config.model_type
    if config.model_name is not None:
        db_config.model_name = config.model_name
    if config.api_base_url is not None:
        db_config.api_base_url = config.api_base_url
    if config.dimension is not None:
        db_config.dimension = config.dimension
    if config.is_active is not None:
        db_config.is_active = config.is_active
        
    db.commit()
    db.refresh(db_config)
    return ResponseModel(data=model_to_dict(db_config))

@router.delete("/{config_id}", response_model=ResponseModel)
def delete_model_config(
    config_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """物理删除某个模型配置"""
    db_config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not db_config:
        return ResponseModel(code=404, msg="模型配置不存在")
    
    db.delete(db_config)
    db.commit()
    return ResponseModel(msg="模型配置删除成功")
