#!/bin/bash
# ================================================
# 智能 RAG 平台一键启动 (Linux/macOS)
# 顺序：检查 .env → venv+pip → Chroma(127.0.0.1) → 等心跳 → 后端 → 前端
# ================================================

set -e

echo "================================================"
echo "           智能 RAG 平台一键启动脚本 (Linux/macOS)"
echo "================================================"
echo ""

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

if [[ ! -f .env && ! -f backend/.env ]]; then
  echo "[!] 未找到 .env"
  echo "    请先执行:  cp .env.example .env"
  echo "    并填写 OPENAI_API_KEY / ENV / LOCAL_DB_NAME / CHROMA_COLLECTION_SUFFIX / UPLOAD_DIR"
  exit 1
fi

echo "[0/4] 准备后端虚拟环境与依赖..."
cd backend
if [[ ! -x venv/bin/python ]]; then
  echo "      创建 venv..."
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install -U pip -q
pip install -r requirements.txt -q
cd ..

CHROMA_BIN="$PROJECT_DIR/backend/venv/bin/chroma"
if [[ ! -x "$CHROMA_BIN" ]]; then
  echo "错误: 未找到 $CHROMA_BIN（请确认 chromadb 已装入 venv）"
  exit 1
fi

echo ""
echo "[1/4] 启动 Chroma (--host 127.0.0.1:8000)..."
"$CHROMA_BIN" run --path ./chroma_data --host 127.0.0.1 --port 8000 &
CHROMA_PID=$!
echo "      Chroma PID=$CHROMA_PID"

echo "      等待心跳就绪..."
for i in $(seq 1 30); do
  if curl -s -m 2 "http://127.0.0.1:8000/api/v2/heartbeat" >/dev/null 2>&1; then
    echo "      Chroma 已就绪 (${i}s)"
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "错误: 30 秒内 Chroma 未就绪"
    kill "$CHROMA_PID" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

echo ""
echo "[2/4] 启动后端 (端口 8001)..."
cd backend
# shellcheck disable=SC1091
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
echo "      Backend PID=$BACKEND_PID"
cd ..
sleep 2

echo ""
echo "[3/4] 启动前端 (端口 5173)..."
cd frontend
if [[ ! -d node_modules ]]; then
  echo "      npm ci ..."
  npm ci || npm install
fi
npm run dev &
FRONTEND_PID=$!
echo "      Frontend PID=$FRONTEND_PID"
cd ..

echo ""
echo "================================================"
echo "              服务启动完成"
echo "================================================"
echo "  前端:     http://127.0.0.1:5173"
echo "  后端:     http://127.0.0.1:8001/docs"
echo "  Chroma:   http://127.0.0.1:8000/api/v2/heartbeat"
echo "  账号:     admin / admin123  (Dashboard 仅管理员)"
echo "  .env:     CHROMA_HOST=127.0.0.1 （须与 chroma --host 一致）"
echo ""
echo "按 Ctrl+C 停止所有服务..."

cleanup() {
  echo ""
  echo "停止所有服务..."
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$CHROMA_PID" 2>/dev/null || true
  echo "所有服务已停止"
  exit 0
}

trap cleanup INT
wait
