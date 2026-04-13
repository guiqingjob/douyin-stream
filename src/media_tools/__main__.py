"""media-tools 模块入口

支持 python -m media_tools 调用
"""

# 导入抖音 CLI 入口
from .cli_main import main

if __name__ == "__main__":
    main()
