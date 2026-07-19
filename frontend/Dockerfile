# 前端：构建静态资源后由 Nginx 托管，并反向代理 /api
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
ENV VITE_API_BASE_URL= \
    VITE_USE_MOCK=false \
    VITE_CHAT_SESSION_API=true \
    VITE_APP_ENV=prod
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
