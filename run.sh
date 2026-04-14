#!/bin/bash
# Media Tools Web 一键启动脚本
# 
# 用法:
#   ./run.sh              # 同时启动后端 API 和前端 React 开发服务器
#   ./run.sh backend      # 仅启动后端 API
#   ./run.sh frontend     # 仅启动前端 React 开发服务器
#   ./run.sh build        # 构建前端静态资源

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 确保在项目根目录运行
cd "$(dirname "$0")"

run_backend() {
    info "启动 FastAPI 后端服务 (端口 8000)..."
    python -m uvicorn media_tools.api.app:app --reload --host 127.0.0.1 --port 8000
}

run_frontend() {
    info "启动 React 前端开发服务器..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        info "安装前端依赖..."
        npm install
    fi
    npm run dev
}

run_both() {
    info "准备同时启动前后端..."
    
    # 后端检查依赖
    if ! python -c "import uvicorn" 2>/dev/null; then
        info "安装后端依赖..."
        pip install -r requirements.txt
    fi

    # 前端检查依赖
    if [ ! -d "frontend/node_modules" ]; then
        info "安装前端依赖..."
        cd frontend && npm install && cd ..
    fi

    # 启动后端在后台
    info "启动后端 (端口 8000)..."
    python -m uvicorn media_tools.api.app:app --reload --host 127.0.0.1 --port 8000 &
    BACKEND_PID=$!

    # 启动前端在前台
    info "启动前端 (Vite)..."
    cd frontend && npm run dev

    # 当脚本退出时关闭后台的 uvicorn
    trap "kill $BACKEND_PID" EXIT
}

build_frontend() {
    info "构建前端生产环境资源..."
    cd frontend
    npm install
    npm run build
    success "构建完成！产物位于 frontend/dist/"
}

case "${1:-}" in
    backend) run_backend ;;
    frontend) run_frontend ;;
    build) build_frontend ;;
    help|--help|-h)
        echo "Media Tools Web 一键启动脚本"
        echo "  ./run.sh           同时启动前后端（开发模式）"
        echo "  ./run.sh backend   仅启动 FastAPI 后端"
        echo "  ./run.sh frontend  仅启动 React 前端"
        echo "  ./run.sh build     构建前端静态资源"
        ;;
    "") run_both ;;
    *)
        error "未知命令: $1"
        exit 1
        ;;
esac