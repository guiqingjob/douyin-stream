#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 功能测试脚本
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def test_ui_module():
    """测试 UI 模块"""
    print("=" * 60)
    print("测试 1: UI 模块")
    print("=" * 60)

    from scripts.core.ui import (
        success,
        error,
        warning,
        info,
        bold,
        print_header,
        print_table,
        format_size,
        format_number,
        ProgressBar,
    )

    print(success("成功消息"))
    print(error("错误消息"))
    print(warning("警告消息"))
    print(info("信息消息"))
    print(f"粗体: {bold('测试文本')}")
    print()

    # 测试表格
    print("表格测试:")
    print_table(
        ["序号", "名称", "大小"],
        [
            [1, "文件 A", "100 MB"],
            [2, "文件 B", "200 MB"],
        ],
    )
    print()

    # 测试格式化
    print(f"格式化大小: {format_size(1234567890)}")
    print(f"格式化数字: {format_number(123456789)}")
    print()

    # 测试进度条
    print("进度条测试:")
    bar = ProgressBar(10, "下载")
    for i in range(10):
        bar.update()
    bar.finish()
    print()

    print(success("✓ UI 模块测试通过"))
    print()


def test_config_module():
    """测试配置模块"""
    print("=" * 60)
    print("测试 2: 配置管理模块")
    print("=" * 60)

    from scripts.core.config_mgr import get_config
    from scripts.core.ui import success

    config = get_config()
    print(f"配置文件路径: {config.config_path}")
    print(f"下载路径: {config.get_download_path()}")
    print(f"数据库路径: {config.get_db_path()}")
    print(f"关注列表路径: {config.get_following_path()}")
    print(f"是否有 Cookie: {config.has_cookie()}")
    print()

    print(success("✓ 配置管理模块测试通过"))
    print()


def test_env_check():
    """测试环境检测"""
    print("=" * 60)
    print("测试 3: 环境检测")
    print("=" * 60)

    from scripts.core.env_check import check_all
    from scripts.core.ui import success, error, info

    all_passed, results = check_all()

    print()
    for name, result in results.items():
        status = "✓" if result["ok"] else "✗"
        print(f"  {status} {name}: {result['message']}")
    print()

    if all_passed:
        print(success("✓ 环境检测通过"))
    else:
        print(error("✗ 环境检测未通过"))
    print()


def test_following_mgr():
    """测试关注列表管理"""
    print("=" * 60)
    print("测试 4: 关注列表管理")
    print("=" * 60)

    from scripts.core.following_mgr import list_users, display_users
    from scripts.core.ui import success, info

    users = list_users()
    print(f"关注列表中有 {len(users)} 位博主")
    print()

    if users:
        display_users()
    else:
        print(info("关注列表为空（这是正常的，如果尚未添加博主）"))
    print()

    print(success("✓ 关注列表管理测试通过"))
    print()


def test_cli_imports():
    """测试 CLI 导入"""
    print("=" * 60)
    print("测试 5: CLI 主程序导入")
    print("=" * 60)

    from scripts.core.ui import success

    # 测试所有 core 模块导入
    from scripts.core import ui
    from scripts.core import config_mgr
    from scripts.core import env_check
    from scripts.core import auth
    from scripts.core import following_mgr
    from scripts.core import downloader
    from scripts.core import compressor
    from scripts.core import data_generator

    print(success("所有 core 模块导入成功"))
    print()


def main():
    """运行所有测试"""
    print()
    print("=" * 60)
    print("  CLI 功能测试")
    print("=" * 60)
    print()

    tests = [
        ("UI 模块", test_ui_module),
        ("配置管理", test_config_module),
        ("环境检测", test_env_check),
        ("关注列表", test_following_mgr),
        ("CLI 导入", test_cli_imports),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} 测试失败: {e}")
            import traceback

            traceback.print_exc()
            print()
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    print()

    if failed == 0:
        print("🎉 所有测试通过！CLI 可以正常使用")
    else:
        print("⚠️  部分测试失败，请检查错误信息")

    print()


if __name__ == "__main__":
    main()
