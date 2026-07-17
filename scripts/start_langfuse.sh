#!/usr/bin/env bash
# 本地启动 Langfuse（可选；未启动时后端会自动跳过追踪上报）
# 文档：https://langfuse.com/docs/deployment/self-host
set -e
echo "请按 Langfuse 官方 docker-compose 启动，默认 UI: http://localhost:3000"
echo "启动后把 PUBLIC/SECRET Key 写入 backend/.env 的 LANGFUSE_* 配置项"
echo "参考：https://github.com/langfuse/langfuse"
