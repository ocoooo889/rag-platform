#!/bin/bash
# 快速重启（不装依赖）：停端口 → Chroma → 等心跳 → 后端 → 前端
set -euo pipefail

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

echo "================================================"
echo "           快速重启开发服务 (跳过 pip / npm)"
echo "================================================"

if [[ ! -f .env && ! -f backend/.env ]]; then
  echo "[!] 未找到 .env"
  exit 1
fi

bash "$(dirname "$0")/stop_all.sh" || true
sleep 1

CHROMA_BIN="$PROJECT_DIR/backend/venv/bin/chroma"
if [[ ! -x "$CHROMA_BIN" ]]; then
  echo "错误: 缺少 chroma，请先 bash scripts/start_all.sh"
  exit 1
fi

echo "[1/3] 启动 Chroma (--host 127.0.0.1)..."
"$CHROMA_BIN" run --path ./chroma_data --host 127.0.0.1 --port 8000 &
CHROMA_PID=$!

for i in $(seq 1 30); do
  if curl -s -m 2 "http://127.0.0.1:8000/api/v2/heartbeat" >/dev/null 2>&1; then
    echo "      Chroma 已就绪 (${i}s)"
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "错误: Chroma 未就绪"
    exit 1
  fi
  sleep 1
done

echo "[2/3] 启动后端..."
cd backend
# shellcheck disable=SC1091
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd ..
sleep 2

echo "[3/3] 启动前端..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "完成。前端 http://127.0.0.1:5173"
echo "请确认 .env 中 CHROMA_HOST=127.0.0.1"
echo "按 Ctrl+C 停止..."

cleanup() {
  kill "$FRONTEND_PID" "$BACKEND_PID" "$CHROMA_PID" 2>/dev/null || true
  exit 0
}
trap cleanup INT
wait
