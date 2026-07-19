@echo off
:: ================================================
:: 快速重启（不停装依赖）：停端口 → Chroma → 等心跳 → 后端 → 前端
:: ================================================
chcp 65001 >nul
set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"
set "PROJECT_DIR=%CD%"

echo ================================================
echo           快速重启开发服务 (无 pip / npm)
echo ================================================
echo.

if not exist ".env" if not exist "backend\.env" (
  echo [!] 未找到 .env ，请先 copy .env.example .env
  pause
  exit /b 1
)

call "%~dp0stop_all.bat" nopause

echo.
echo [1/3] 启动 Chroma (--host 127.0.0.1:8000)...
if not exist "backend\venv\Scripts\chroma.exe" (
  echo 错误: 缺少 chroma.exe，请先运行 scripts\start_all.bat 安装依赖
  pause
  exit /b 1
)
start "Chroma" /D "%PROJECT_DIR%" cmd /k "backend\venv\Scripts\chroma.exe run --path ./chroma_data --host 127.0.0.1 --port 8000"

echo       等待心跳...
set /a _tries=0
:wait_chroma
set /a _tries+=1
curl.exe -s -m 2 http://127.0.0.1:8000/api/v2/heartbeat >nul 2>&1
if not errorlevel 1 goto chroma_ready
if %_tries% GEQ 30 (
  echo 错误: Chroma 未就绪
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_chroma
:chroma_ready
echo       Chroma 已就绪 (%_tries%s)

echo [2/3] 启动后端...
start "Backend" /D "%PROJECT_DIR%\backend" cmd /k "venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
timeout /t 2 /nobreak >nul

echo [3/3] 启动前端...
start "Frontend" /D "%PROJECT_DIR%\frontend" cmd /k "npm run dev"

echo.
echo 完成。前端 http://127.0.0.1:5173  Chroma http://127.0.0.1:8000/api/v2/heartbeat
echo 请确认 .env 中 CHROMA_HOST=127.0.0.1
pause
