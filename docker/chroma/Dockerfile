# 与 backend 依赖对齐的 Chroma 服务（避免依赖 Docker Hub 特定 tag）
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install "chromadb==1.5.9" "bcrypt>=4.0.0,<5.0.0"

RUN mkdir -p /data
WORKDIR /data
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=8 \
  CMD curl -sf http://127.0.0.1:8000/api/v2/heartbeat || exit 1

CMD ["chroma", "run", "--host", "0.0.0.0", "--port", "8000", "--path", "/data"]
