import os
import uuid
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from app.db.database import sync_engine, Base
from app.api import auth, roles, users, user_groups, kb, docs, branding, models as api_models
from app.utils.logger import logger, request_id_var, user_id_var, action_var

# 初始化数据库表结构
Base.metadata.create_all(bind=sync_engine)

# 自动填充初始基础数据（角色、超级管理员、白标默认配置）
def init_db_data():
    from app.db.database import SessionLocal
    from app.db.models import Role, User, SystemConfig
    from app.utils.auth import get_password_hash
    from app.api.branding import DEFAULTS
    
    db = SessionLocal()
    try:
        # 1. 创建内置的角色
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", permissions=["*"])
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
            
        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(name="user", permissions=["kb:view", "doc:view", "chat:send"])
            db.add(user_role)
            db.commit()
            
        # 2. 创建内置的超级管理员账号
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                display_name="系统管理员",
                role_id=admin_role.id,
                status="启用"
            )
            db.add(admin_user)
            db.commit()
            
        # 3. 填充默认的系统白标配置
        for k, v in DEFAULTS.items():
            config = db.query(SystemConfig).filter(SystemConfig.config_key == k).first()
            if not config:
                config = SystemConfig(config_key=k, config_value=v)
                db.add(config)
        db.commit()
    except Exception as e:
        logger.error(f"预置基础数据库数据异常: {str(e)}")
    finally:
        db.close()

init_db_data()

app = FastAPI(title="智能 RAG 平台后台接口")

# 配置 CORS 中间件允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段放行，生产环境需替换为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 request_id 日志中间件，为每个请求生成唯一 UUID
@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # 绑定变量到当前协程上下文
    request_id_token = request_id_var.set(request_id)
    user_id_token = user_id_var.set(0)
    action_token = action_var.set(f"{request.method} {request.url.path}")
    
    start_time = time.time()
    logger.info(f"收到请求: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        logger.bind(duration_ms=duration_ms).info(
            f"请求结束: {request.method} {request.url.path} - 状态码: {response.status_code} - 耗时: {duration_ms}ms"
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.bind(duration_ms=duration_ms).error(
            f"请求处理异常: {request.method} {request.url.path} - 耗时: {duration_ms}ms - 错误: {str(e)}"
        )
        raise e
    finally:
        # 重置协程上下文变量，避免污染
        request_id_var.reset(request_id_token)
        user_id_var.reset(user_id_token)
        action_var.reset(action_token)

# 1. 全局异常拦截 - 422 验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=200,
        content={"code": 400, "msg": "参数校验错误或必填字段为空", "data": exc.errors()}
    )

# 2. 全局异常拦截 - HTTP 异常 (例如 401 未登录)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=200,
        content={"code": exc.status_code, "msg": str(exc.detail), "data": None}
    )

# 3. 全局异常拦截 - 服务器内部错误
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={"code": 500, "msg": f"服务内部异常: {str(exc)}", "data": None}
    )

# 注册 Prometheus 接口监控采集端点
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 注册所有已实现的 API 路由
app.include_router(auth.router)
app.include_router(roles.router)
app.include_router(users.router)
app.include_router(user_groups.router)
app.include_router(kb.router)
app.include_router(docs.router)
app.include_router(branding.router)
app.include_router(api_models.router)

# 动态/安全导入并注册后端 A 的检索与对话路由，避免空文件报错
try:
    from app.api import rag, chat
    if hasattr(rag, "router"):
        app.include_router(rag.router)
    if hasattr(chat, "router"):
        app.include_router(chat.router)
except (ImportError, AttributeError) as e:
    logger.warning(f"后端 A 的接口尚未就绪，跳过注册: {str(e)}")

# 挂载白标静态文件目录
from fastapi.staticfiles import StaticFiles
os.makedirs("./uploads/branding", exist_ok=True)
app.mount("/uploads/branding", StaticFiles(directory="./uploads/branding"), name="branding")

@app.get("/")
def read_root():
    return {"code": 0, "msg": "RAG API is running"}
