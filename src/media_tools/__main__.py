"""media-tools 模块入口

支持 python -m media_tools 调用
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(project_root))

# 导入抖音 CLI 入口
from cli import main_menu

if __name__ == "__main__":
    main_menu()
