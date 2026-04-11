#!/bin/bash
# Media Tools 快速启动脚本
# 
# 用法:
#   ./run.sh              # 启动CLI V2（推荐）
#   ./run.sh v1           # 启动CLI V1（旧版）
#   ./run.sh demo         # 运行功能演示
#   ./run.sh test         # 运行测试
#   ./run.sh diag         # 运行诊断检查
#   ./run.sh setup        # 初始化环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "未找到Python3，请先安装Python 3.11+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    info "Python版本: $PYTHON_VERSION"
}

# 检查依赖
check_deps() {
    info "检查依赖安装..."
    if ! python3 -c "import rich" 2>/dev/null; then
        warn "依赖未安装，正在安装..."
        pip3 install -r requirements.txt
        success "依赖安装完成"
    else
        success "依赖已安装"
    fi
}

# 检查Playwright
check_playwright() {
    if ! python3 -c "import playwright" 2>/dev/null; then
        warn "Playwright未安装，正在安装..."
        playwright install chromium
        success "Playwright安装完成"
    fi
}

# 初始化环境
setup() {
    info "初始化环境..."
    check_python
    
    # 创建必要目录
    mkdir -p downloads transcripts logs config/transcribe .auth
    
    # 复制配置模板
    if [ ! -f config/config.yaml ]; then
        cp config/config.yaml.example config/config.yaml
        success "创建 config/config.yaml"
    fi
    
    if [ ! -f config/following.json ]; then
        cp config/following.json.example config/following.json
        success "创建 config/following.json"
    fi
    
    if [ ! -f config/transcribe/.env ]; then
        cp config/transcribe/.env.example config/transcribe/.env
        success "创建 config/transcribe/.env"
    fi
    
    check_deps
    check_playwright
    
    success "环境初始化完成！"
    echo ""
    echo "下一步: 运行 ./run.sh 启动CLI"
}

# 启动CLI V2
run_v2() {
    info "启动 Media Tools CLI V2..."
    python3 cli_v2.py
}

# 启动CLI V1
run_v1() {
    info "启动 Media Tools CLI V1..."
    python3 cli.py
}

# 运行演示
run_demo() {
    info "运行V2功能演示..."
    python3 demo_v2_features.py
}

# 运行测试
run_test() {
    info "运行V2新功能测试..."
    python3 test_v2_features.py
}

# 运行诊断
run_diag() {
    info "运行全面诊断..."
    python3 -m src.media_tools.error_diagnosis --full
}

# 显示帮助
show_help() {
    echo "Media Tools 快速启动脚本"
    echo ""
    echo "用法:"
    echo "  ./run.sh [command]"
    echo ""
    echo "命令:"
    echo "  (无)     启动CLI V2（推荐）"
    echo "  v1       启动CLI V1（旧版）"
    echo "  demo     运行功能演示"
    echo "  test     运行测试"
    echo "  diag     运行诊断检查"
    echo "  setup    初始化环境"
    echo "  help     显示此帮助"
    echo ""
}

# 主函数
main() {
    case "${1:-}" in
        setup)
            setup
            ;;
        v1)
            run_v1
            ;;
        demo)
            run_demo
            ;;
        test)
            run_test
            ;;
        diag)
            run_diag
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            run_v2
            ;;
        *)
            error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
