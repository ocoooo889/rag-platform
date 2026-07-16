import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document, KnowledgeBase, User
from app.schema.schemas import ResponseModel
from app.api.auth import get_current_user
from app.utils.permission import require_kb_access

router = APIRouter(prefix="/api", tags=["documents"])

# 支持从环境变量中读取上传目录，提供兜底路径
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/dev_default")

def doc_to_dict(doc: Document):
    return {
        "id": doc.id,
        "kb_id": doc.kb_id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat() if doc.created_at else None
    }

@router.post("/knowledge-bases/{kb_id}/documents/upload", response_model=ResponseModel)
async def upload_document(
    kb_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """上传文档到特定知识库。上传前会检查该知识库是否存在，并校验用户是否有权限访问"""
    # 1. 权限拦截校验
    await require_kb_access(kb_id, current_user, db)
    
    # 2. 检查知识库是否存在
    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        return ResponseModel(code=404, msg="知识库不存在")

    # 3. 文件后缀限制
    if not file.filename.endswith(('.md', '.txt')):
        return ResponseModel(code=400, msg="仅支持 .md 和 .txt 文件格式")

    # 创建上传目录并写入文件
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        return ResponseModel(code=500, msg=f"文件写入失败: {str(e)}")
        
    file_size = os.path.getsize(file_path)
    # 文件大小校验（最大 10MB）
    if file_size > 10 * 1024 * 1024:
        try:
            os.remove(file_path)
        except OSError:
            pass
        return ResponseModel(code=400, msg="文件大小超过 10MB 限制")

    file_type = "md" if file.filename.endswith(".md") else "txt"
    
    # 创建数据库记录，初始状态为 pending 挂起
    new_doc = Document(
        kb_id=kb_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        status="pending"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    return ResponseModel(data=doc_to_dict(new_doc))

@router.get("/knowledge-bases/{kb_id}/documents", response_model=ResponseModel)
async def get_documents(
    kb_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """获取指定知识库下的所有文档列表，内置权限校验"""
    # 1. 权限拦截校验
    await require_kb_access(kb_id, current_user, db)
    
    # 2. 查询数据并返回
    docs = db.query(Document).filter(Document.kb_id == kb_id).all()
    return ResponseModel(data=[doc_to_dict(d) for d in docs])

@router.delete("/documents/{doc_id}", response_model=ResponseModel)
async def delete_document(
    doc_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """删除文档。执行删除前会检查文档所属的知识库，并对用户校验该知识库的修改权"""
    db_doc = db.query(Document).filter(Document.id == doc_id).first()
    if not db_doc:
        return ResponseModel(code=404, msg="文档不存在")
    
    # 1. 跨库/跨组权限校验，检查对文档所属的知识库是否有读写访问权
    await require_kb_access(db_doc.kb_id, current_user, db)
    
    # 2. 物理删除本地存储中的上传文件
    file_path = os.path.join(UPLOAD_DIR, db_doc.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
        
    db.delete(db_doc)
    db.commit()
    return ResponseModel(msg="文档删除成功")
