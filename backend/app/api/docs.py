import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document, KnowledgeBase, User
from app.schema.response_schema import ResponseModel
from app.api.auth import get_current_user
from app.utils.permission import require_kb_access
from app.config import UPLOAD_DIR
from app.rag_engine.ingest import ingest_document
from app.rag_engine.embedder import delete_from_chroma
from app.utils.logger import logger
from app.utils.ids import new_id

router = APIRouter(prefix="/api", tags=["documents"])

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
    kb_id: str, 
    background_tasks: BackgroundTasks,
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
    
    # 创建数据库记录，初始状态为 pending 挂起，ID采用契约字符串ID
    new_doc = Document(
        id=new_id("d"),
        kb_id=kb_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        status="pending"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # V2 修复：异步开始进行文档入库切片向量化处理
    background_tasks.add_task(
        ingest_document,
        kb_id=kb_id,
        doc_id=new_doc.id,
        file_path=file_path,
        filename=file.filename
    )
    
    return ResponseModel(data=doc_to_dict(new_doc))

@router.get("/knowledge-bases/{kb_id}/documents", response_model=ResponseModel)
async def get_documents(
    kb_id: str, 
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
    doc_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """删除文档。执行删除前会检查文档所属的知识库，并对用户校验该知识库的修改权"""
    db_doc = db.query(Document).filter(Document.id == doc_id).first()
    if not db_doc:
        return ResponseModel(code=404, msg="文档不存在")
    
    # 1. 跨库/跨组权限校验，检查对文档所属的知识库是否有读写访问权
    await require_kb_access(db_doc.kb_id, current_user, db)
    
    # 2. 从 Chroma 向量库中物理清除该文档所有的切片向量（V2 修复）
    chroma_ids = [chunk.chroma_id for chunk in db_doc.chunks if chunk.chroma_id]
    if chroma_ids:
        try:
            await delete_from_chroma(chroma_ids)
            logger.info(f"成功从 Chroma 删除文档 doc_id={doc_id} 的 {len(chroma_ids)} 个分片向量")
        except Exception as e:
            logger.error(f"从 Chroma 向量库删除分片向量失败: {e}")
            
    # 3. 物理删除本地存储中的上传文件
    file_path = os.path.join(UPLOAD_DIR, db_doc.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
        
    db.delete(db_doc)
    db.commit()
    return ResponseModel(msg="文档删除成功")
