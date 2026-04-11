#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@deprecated
此脚本已废弃，请使用新的 CLI 统一入口:
    python cli.py

本文件仅为向后兼容保留，将在未来版本中移除。
"""

import sys
from pathlib import Path

print("=" * 60)
print("⚠️  警告：此脚本已废弃！")
print("=" * 60)
print()
print("请使用新的 CLI 统一入口：")
print("  python cli.py")
print()
print("新功能：")
print("  ✓ 交互式菜单，只需运行一个命令")
print("  ✓ 统一配置和日志管理")
print("  ✓ 更友好的错误提示")
print()
print("正在启动新 CLI...")
print()

# 启动新 CLI
cli_path = Path(__file__).parent.parent / "cli.py"
sys.argv[0] = str(cli_path)
exec(open(cli_path, "r", encoding="utf-8").read())
