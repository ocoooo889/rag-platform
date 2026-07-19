@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist ".env" (
  echo [!] 缺少 .env，请先 copy .env.example .env 并填写 OPENAI_API_KEY
  pause
  exit /b 1
)
echo Building and starting on http://localhost:8520 ...
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo 若报镜像站 DNS 失败，请检查 Docker Desktop registry-mirrors 配置。
  pause
  exit /b 1
)
echo.
echo 完成。访问 http://localhost:8520
docker compose ps
pause
