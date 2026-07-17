"""数据库建表与种子数据（与 ORM models 对齐，修复 init_db 旧契约不一致问题）"""

from __future__ import annotations

from app.db.database import Base, SessionLocal, sync_engine
from app.db.models import Role, User, SystemConfig
from app.utils.auth import get_password_hash
from app.utils.logger import logger

# 白标默认项（与 branding.DEFAULTS 保持一致）
_BRANDING_DEFAULTS = {
    "brand_name": "RAG 智能知识平台",
    "brand_logo_url": "/uploads/branding/logo.png",
    "brand_favicon_url": "/uploads/branding/favicon.ico",
    "brand_theme_color": "#409EFF",
    "brand_login_title": "企业知识，智能问答",
    "brand_footer_text": "Powered by RAG Platform",
}


def init_schema_and_seed() -> None:
    """create_all 建齐 ORM 表，并写入 admin / 角色 / 白标默认配置。"""
    # 确保模型已注册到 metadata
    import app.db.models  # noqa: F401

    Base.metadata.create_all(bind=sync_engine)

    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", permissions=["*"])
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            db.add(
                Role(
                    name="user",
                    permissions=["kb:view", "doc:view", "chat:send", "rag:test"],
                )
            )
            db.commit()

        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            db.add(
                User(
                    username="admin",
                    hashed_password=get_password_hash("admin123"),
                    display_name="系统管理员",
                    role_id=admin_role.id,
                    status="启用",
                )
            )
            db.commit()

        for key, value in _BRANDING_DEFAULTS.items():
            row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if not row:
                db.add(SystemConfig(config_key=key, config_value=value))
        db.commit()
        logger.info("数据库表结构与种子数据已就绪")
    except Exception as e:
        db.rollback()
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        db.close()
