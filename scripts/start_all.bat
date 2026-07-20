@echo off
:: ================================================
:: 智能 RAG 平台一键启动 (Windows)
:: 顺序：检查 .env → venv+pip → Chroma(127.0.0.1) → 等心跳 → 后端 → 前端
:: ================================================
chcp 65001 >nul
echo ================================================
echo           智能 RAG 平台一键启动脚本 (Windows)
echo ================================================
echo.

set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"
set "PROJECT_DIR=%CD%"

if not exist ".env" if not exist "backend\.env" (
  echo [!] 未找到 .env
  echo     请先执行:  copy .env.example .env
  echo     并填写 OPENAI_API_KEY / ENV / LOCAL_DB_NAME / CHROMA_COLLECTION_SUFFIX / UPLOAD_DIR
  echo.
  pause
  exit /b 1
)

echo [0/4] 准备后端虚拟环境与依赖...
cd backend
if not exist "venv\Scripts\python.exe" (
  echo       创建 venv...
  python -m venv venv
  if errorlevel 1 (
    echo       错误: 创建 venv 失败，请确认已安装 Python 3.10-3.12
    cd /d "%PROJECT_DIR%"
    pause
    exit /b 1
  )
)
echo       pip install -r requirements.txt ...
call venv\Scripts\activate.bat
python -m pip install -U pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
  echo       错误: pip install 失败
  cd /d "%PROJECT_DIR%"
  pause
  exit /b 1
)
cd /d "%PROJECT_DIR%"

echo.
echo [1/4] 启动 Chroma (--host 127.0.0.1:8000，避免 Windows 只绑 ::1)...
if not exist "backend\venv\Scripts\chroma.exe" (
  echo       错误: 未找到 backend\venv\Scripts\chroma.exe
  echo       请确认 chromadb 已安装到 venv
  pause
  exit /b 1
)
start "Chroma" /D "%PROJECT_DIR%" cmd /k "backend\venv\Scripts\chroma.exe run --path ./chroma_data --host 127.0.0.1 --port 8000"

echo       等待 Chroma 心跳就绪...
set /a _tries=0
:wait_chroma
set /a _tries+=1
curl.exe -s -m 2 http://127.0.0.1:8000/api/v2/heartbeat >nul 2>&1
if not errorlevel 1 goto chroma_ready
if %_tries% GEQ 30 (
  echo       错误: 30 秒内 Chroma 未就绪，请检查 chroma 窗口日志
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_chroma
:chroma_ready
echo       Chroma 已就绪 (%_tries%s)

echo.
echo [2/5] 启动后端 (端口 8001)...
start "Backend" /D "%PROJECT_DIR%\backend" cmd /k "venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
timeout /t 2 /nobreak >nul

echo.
echo [3/5] 启动 Rerank 微服务 (端口 8002)...
start "Rerank" /D "%PROJECT_DIR%\backend" cmd /k "venv\Scripts\activate.bat && set HTTP_PROXY=&& set HTTPS_PROXY=&& set http_proxy=&& set https_proxy=&& uvicorn rerank_service.main:app --host 127.0.0.1 --port 8002 --reload"
timeout /t 1 /nobreak >nul

echo.
echo [4/5] 启动前端 (端口 5173)...
cd frontend
if not exist "node_modules" (
  echo       npm ci / npm install...
  call npm ci 2>nul || call npm install
)
start "Frontend" /D "%PROJECT_DIR%\frontend" cmd /k "npm run dev"
cd /d "%PROJECT_DIR%"

echo.
echo ================================================
echo              服务启动完成
echo ================================================
echo   前端:     http://127.0.0.1:5173
echo   后端:     http://127.0.0.1:8001/docs
echo   Rerank:   http://127.0.0.1:8002/health
echo   Chroma:   http://127.0.0.1:8000/api/v2/heartbeat
echo   账号:     admin / admin123  (Dashboard 仅管理员)
echo   .env:     CHROMA_HOST=127.0.0.1 （须与 chroma --host 一致）
echo.
pause
