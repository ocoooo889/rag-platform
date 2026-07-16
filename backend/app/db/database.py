import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

db_name = os.getenv("LOCAL_DB_NAME", "dev_default_rag.db")

# 同步配置，用于部分常规 CRUD 操作及表初始化
SYNC_DB_URL = f"sqlite:///./{db_name}"
sync_engine = create_engine(SYNC_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# 异步配置，用于高性能异步查询与并发检索
ASYNC_DB_URL = f"sqlite+aiosqlite:///./{db_name}"
async_engine = create_async_engine(ASYNC_DB_URL, connect_args={"check_same_thread": False})
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
)

Base = declarative_base()

# 同步数据库会话依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 异步数据库会话依赖项
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
