@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0.."
set "OUT_DIR=%CD%\dist-docker"
set "STAGE=%OUT_DIR%\rag-platform-docker-8520"
set "ZIP=%OUT_DIR%\rag-platform-docker-8520.zip"

echo ========================================
echo   Pack Docker deploy zip (port 8520)
echo ========================================

if exist "%STAGE%" rmdir /s /q "%STAGE%"
if exist "%ZIP%" del /f /q "%ZIP%"
mkdir "%STAGE%\backend" 2>nul
mkdir "%STAGE%\frontend" 2>nul
mkdir "%STAGE%\docker\chroma" 2>nul
mkdir "%STAGE%\docs" 2>nul
mkdir "%STAGE%\scripts" 2>nul

copy /y "docker-compose.yml" "%STAGE%\" >nul
copy /y ".dockerignore" "%STAGE%\" >nul
copy /y ".env.example" "%STAGE%\" >nul
copy /y "backend\Dockerfile" "%STAGE%\backend\" >nul
copy /y "backend\requirements.txt" "%STAGE%\backend\" >nul
copy /y "frontend\Dockerfile" "%STAGE%\frontend\" >nul
copy /y "frontend\nginx.conf" "%STAGE%\frontend\" >nul
copy /y "docker\chroma\Dockerfile" "%STAGE%\docker\chroma\" >nul
copy /y "docker\发给组员-必读.txt" "%STAGE%\" >nul
copy /y "docs\Docker部署说明.md" "%STAGE%\docs\" >nul
copy /y "scripts\docker_up.bat" "%STAGE%\scripts\" >nul
copy /y "scripts\pack_docker_images.bat" "%STAGE%\scripts\" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%STAGE%\*' -DestinationPath '%ZIP%' -Force"

if not exist "%ZIP%" (
  echo FAIL: zip not created
  exit /b 1
)

echo OK: %ZIP%
for %%A in ("%ZIP%") do echo Size: %%~zA bytes
endlocal
