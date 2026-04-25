# Media Tools — 多阶段构建
# 阶段1: Node.js 构建前端
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 阶段2: Python 运行时
FROM python:3.11-slim AS runtime

# 安装 Playwright 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libx11-6 \
    libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libcurl4 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e "." playwright && \
    playwright install chromium

# 复制源码
COPY src/ ./src/
COPY config/ ./config/

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist /app/static

# 创建数据持久化目录
RUN mkdir -p /app/data/downloads /app/data/transcripts

ENV PYTHONPATH=/app/src
ENV MEDIA_TOOLS_PROJECT_ROOT=/app
EXPOSE 8000

VOLUME ["/app/data"]

CMD ["python", "-m", "uvicorn", "media_tools.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
