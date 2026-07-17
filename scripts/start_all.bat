@echo off
:: ================================================
:: 智能 RAG 平台一键启动脚本 (Windows)
:: 【项目负责人补充内容】
:: 功能：一键启动 Chroma + 后端 + 前端
:: ================================================
chcp 65001 >nul
echo ================================================
echo           智能 RAG 平台一键启动脚本 (Windows)
echo           【项目负责人补充内容】
echo ================================================
echo.

set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

echo [1/3] 启动 Chroma 向量库服务 (端口 8000)...
start "Chroma" cmd /k "chroma run --path ./chroma_data --port 8000"
echo       Chroma 服务已启动，等待 3 秒...
timeout /t 3 /nobreak >nul

echo.
echo [2/3] 启动后端服务 (端口 8001)...
cd backend
if not exist venv (
    echo       创建虚拟环境...
    python -m venv venv
)
echo       激活虚拟环境并启动后端...
start "Backend" cmd /k "venv\Scripts\activate && pip install -r requirements.txt -q && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
cd ..
echo       后端服务已启动，等待 5 秒...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] 启动前端服务 (端口 5173)...
cd frontend
if not exist node_modules (
    echo       安装前端依赖...
    npm install
)
echo       启动前端开发服务器...
start "Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ================================================
echo              服务启动完成！
echo ================================================
echo.
echo 访问地址：
echo   - 前端页面:    http://localhost:5173
echo   - 后端接口:    http://localhost:8001
echo   - 接口文档:    http://localhost:8001/docs
echo   - Chroma API:  http://localhost:8000
echo.
echo 按任意键退出...
pause >nul