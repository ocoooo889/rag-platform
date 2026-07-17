from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Role, User
from app.schema.request_schema import RoleCreate, RoleUpdate
from app.schema.response_schema import ResponseModel
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/roles", tags=["roles"])

def role_to_dict(role: Role):
    return {
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions
    }

@router.post("", response_model=ResponseModel)
def create_role(
    role: RoleCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """创建新角色"""
    db_role = db.query(Role).filter(Role.name == role.name).first()
    if db_role:
        return ResponseModel(code=400, msg="角色名已存在")
    
    new_role = Role(name=role.name, permissions=role.permissions)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return ResponseModel(data=role_to_dict(new_role))

@router.get("", response_model=ResponseModel)
def get_roles(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """获取所有角色列表"""
    roles = db.query(Role).all()
    return ResponseModel(data=[role_to_dict(r) for r in roles])

@router.put("/{role_id}", response_model=ResponseModel)
def update_role(
    role_id: int, 
    role: RoleUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """更新角色信息"""
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        return ResponseModel(code=404, msg="角色不存在")
    
    db_role.name = role.name
    db_role.permissions = role.permissions
    db.commit()
    db.refresh(db_role)
    return ResponseModel(data=role_to_dict(db_role))

@router.delete("/{role_id}", response_model=ResponseModel)
def delete_role(
    role_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """删除角色。若角色下有绑定的用户，则拒绝删除"""
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        return ResponseModel(code=404, msg="角色不存在")
    
    if db_role.users:
        return ResponseModel(code=400, msg="角色下有关联用户，无法删除")
    
    db.delete(db_role)
    db.commit()
    return ResponseModel(msg="角色删除成功")
