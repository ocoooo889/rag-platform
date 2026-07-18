@echo off
:: 停止本机 RAG 开发常用端口上的监听进程（8000 / 8001 / 5173）
setlocal EnableExtensions
chcp 65001 >nul

echo 正在停止端口 8000 / 8001 / 5173 上的进程 ...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ports = 8000,8001,5173; foreach ($port in $ports) { Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ('Stopping PID ' + $_.OwningProcess + ' on port ' + $port); Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"

echo 完成。
pause
endlocal
