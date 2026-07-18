#!/usr/bin/env bash
# 停止常用开发端口上的进程（8000 / 8001 / 5173）
set -euo pipefail

for port in 8000 8001 5173; do
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
      echo "Stopping port $port: $pids"
      kill $pids 2>/dev/null || true
    fi
  elif command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" 2>/dev/null || true
  else
    echo "请安装 lsof 或 fuser 以自动停止端口 $port"
  fi
done

echo "完成"
