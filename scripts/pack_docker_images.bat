@echo off
:: 将已构建的 compose 镜像导出为 tar，便于离线发给组员
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0.."
set "OUT_DIR=%CD%\dist-docker"
set "TAR=%OUT_DIR%\rag-platform-images-8520.tar"

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo ========================================
echo   导出 Docker 镜像（体积可能很大）
echo ========================================
echo 请先成功执行: docker compose build
echo.

docker compose build
if errorlevel 1 (
  echo 构建失败，无法导出
  pause
  exit /b 1
)

echo.
echo 正在 docker save ...
docker save -o "%TAR%" ^
  rag-platform-backend:latest ^
  rag-platform-frontend:latest ^
  rag-platform-chroma:latest

if errorlevel 1 (
  echo.
  echo 若镜像名不匹配，请先运行: docker images
  echo 再手动: docker save -o dist-docker\rag-platform-images-8520.tar IMAGE1 IMAGE2 IMAGE3
  pause
  exit /b 1
)

echo.
echo 完成：%TAR%
echo 对方执行: docker load -i rag-platform-images-8520.tar
echo 然后在有 docker-compose.yml 的目录: docker compose up -d
echo.
explorer "%OUT_DIR%"
pause
endlocal
