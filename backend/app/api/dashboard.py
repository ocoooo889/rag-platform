from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import KnowledgeBase, Document, User, UserGroup

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取数据大盘统计"""
    kb_count = db.query(KnowledgeBase).count()
    doc_count = db.query(Document).count()
    user_count = db.query(User).count()
    group_count = db.query(UserGroup).count()
    
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "kb_count": kb_count,
            "doc_count": doc_count,
            "user_count": user_count,
            "group_count": group_count
        }
    }
