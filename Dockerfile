# 使用 Python 3.11
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright浏览器
RUN playwright install chromium && playwright install-deps chromium

# 复制项目文件
COPY . .

# 创建必要目录
RUN mkdir -p downloads transcripts logs config .auth

# 复制配置模板
RUN cp config/config.yaml.example config/config.yaml 2>/dev/null || true
RUN cp config/following.json.example config/following.json 2>/dev/null || true

# 暴露端口（如果需要Web面板）
EXPOSE 8000

# 默认命令
CMD ["python", "cli_v2.py"]
