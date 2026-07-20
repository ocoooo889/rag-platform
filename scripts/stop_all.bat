@echo off
:: 停止本机 RAG 开发常用端口上的监听进程（8000 / 8001 / 8002 / 5173）
:: 传参 nopause 时不 pause（供 restart_dev 调用）
setlocal EnableExtensions
chcp 65001 >nul

echo 正在停止端口 8000 / 8001 / 8002 / 5173 上的进程 ...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ports = 8000,8001,8002,5173; foreach ($port in $ports) { Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $op = $_.OwningProcess; if ($op) { Write-Host ('Stopping PID ' + $op + ' on port ' + $port); Stop-Process -Id $op -Force -ErrorAction SilentlyContinue; Start-Process -FilePath taskkill -ArgumentList @('/F','/T','/PID',\"$op\") -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue } } }; Start-Sleep -Seconds 1; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'uvicorn app.main|rerank_service|chroma.exe run|vite|multiprocessing.spawn') } | ForEach-Object { Write-Host ('Stopping leftover PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Seconds 1"

echo 完成。
if /I not "%~1"=="nopause" pause
endlocal
