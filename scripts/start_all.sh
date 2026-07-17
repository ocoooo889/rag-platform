#!/bin/bash

# ================================================
# 智能 RAG 平台一键启动脚本 (Linux/Mac)
# 【项目负责人补充内容】
# 功能：一键启动 Chroma + 后端 + 前端
# ================================================

set -e

echo "================================================"
echo "           智能 RAG 平台一键启动脚本 (Linux/Mac)"
echo "           【项目负责人补充内容】"
echo "================================================"
echo ""

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

echo "[1/3] 启动 Chroma 向量库服务 (端口 8000)..."
if command -v chroma &> /dev/null; then
    chroma run --path ./chroma_data --port 8000 &
    CHROMA_PID=$!
    echo "      Chroma 服务已启动 (PID: $CHROMA_PID)"
else
    echo "      错误: chroma 命令未找到，请先安装 chromadb"
    echo "      安装命令: pip install chromadb"
    exit 1
fi
echo "      等待 3 秒..."
sleep 3

echo ""
echo "[2/3] 启动后端服务 (端口 8001)..."
cd backend
if [ ! -d "venv" ]; then
    echo "      创建虚拟环境..."
    python3 -m venv venv
fi
echo "      激活虚拟环境并启动后端..."
source venv/bin/activate
pip install -r requirements.txt -q
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
echo "      后端服务已启动 (PID: $BACKEND_PID)"
cd ..
echo "      等待 5 秒..."
sleep 5

echo ""
echo "[3/3] 启动前端服务 (端口 5173)..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "      安装前端依赖..."
    npm install
fi
echo "      启动前端开发服务器..."
npm run dev &
FRONTEND_PID=$!
echo "      前端服务已启动 (PID: $FRONTEND_PID)"
cd ..

echo ""
echo "================================================"
echo "              服务启动完成！"
echo "================================================"
echo ""
echo "访问地址："
echo "  - 前端页面:    http://localhost:5173"
echo "  - 后端接口:    http://localhost:8001"
echo "  - 接口文档:    http://localhost:8001/docs"
echo "  - Chroma API:  http://localhost:8000"
echo ""
echo "服务进程："
echo "  - Chroma:      $CHROMA_PID"
echo "  - Backend:     $BACKEND_PID"
echo "  - Frontend:    $FRONTEND_PID"
echo ""
echo "按 Ctrl+C 停止所有服务..."

cleanup() {
    echo ""
    echo "停止所有服务..."
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    kill $CHROMA_PID 2>/dev/null || true
    echo "所有服务已停止"
    exit 0
}

trap cleanup INT

wait