#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检测模块 - 检查 Python 版本、依赖和配置
"""

import subprocess
import sys
from pathlib import Path

from .ui import error, header, info, print_header, print_status, separator, success
from .config_mgr import get_config


def check_python_version():
    """
    检查 Python 版本

    Returns:
        (is_ok, message) 元组
    """
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    # f2 支持 Python 3.9 - 3.13
    if version.major == 3 and 9 <= version.minor <= 13:
        return True, f"Python {version_str} (兼容 3.9-3.13)"
    else:
        return False, f"Python {version_str} (需要 3.9-3.13)"


def check_package_installed(package_name):
    """
    检查 Python 包是否已安装

    Args:
        package_name: 包名

    Returns:
        (is_ok, version_or_error) 元组
    """
    try:
        result = subprocess.run(
            ["pip", "show", package_name], capture_output=True, text=True
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    return True, version
            return True, "已安装"
        else:
            return False, "未安装"
    except Exception as e:
        return False, str(e)


def check_playwright_browsers():
    """
    检查 Playwright 浏览器内核是否安装

    Returns:
        (is_ok, message) 元组
    """
    try:
        result = subprocess.run(
            ["python", "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True,
        )
        # 如果命令失败，说明浏览器未安装
        if result.returncode != 0:
            return False, "未安装（运行 python -m playwright install chromium）"
        return True, "已安装"
    except Exception:
        # 备用检查方式
        home = Path.home()
        cache_dir = home / ".cache" / "ms-playwright"
        if cache_dir.exists():
            return True, "已安装"
        return False, "未安装（运行 python -m playwright install chromium）"


def check_ffmpeg():
    """
    检查 ffmpeg 是否安装

    Returns:
        (is_ok, message) 元组
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            # 提取版本号
            first_line = result.stdout.split("\n")[0]
            return True, first_line
        return False, "未安装"
    except FileNotFoundError:
        return False, "未安装"


def check_config():
    """
    检查配置文件

    Returns:
        (is_ok, message) 元组
    """
    try:
        config = get_config()
        is_valid, errors = config.validate()

        if is_valid:
            return True, "配置正常"
        else:
            return False, "配置问题: " + "; ".join(errors)
    except Exception as e:
        return False, str(e)


def check_all():
    """
    执行全部环境检查

    Returns:
        (all_passed, results_dict) 元组
    """
    print_header("环境检测")

    checks = [
        ("Python 版本", check_python_version),
        ("f2", lambda: check_package_installed("f2")),
        ("playwright", lambda: check_package_installed("playwright")),
        ("Playwright 浏览器", check_playwright_browsers),
        ("ffmpeg", check_ffmpeg),
        ("配置文件", check_config),
    ]

    results = {}
    all_passed = True

    for name, check_func in checks:
        is_ok, message = check_func()
        results[name] = {"ok": is_ok, "message": message}

        if is_ok:
            print_status("success", f"{name}: {message}")
        else:
            print_status("error", f"{name}: {message}")
            all_passed = False

    print()
    if all_passed:
        print(success("✓ 环境检测通过，可以正常使用!"))
    else:
        print(error("✗ 环境检测未通过，请先配置环境"))
        print()
        print(info("安装指南:"))
        print("  1. pip install -r requirements.txt")
        print("  2. python -m playwright install chromium")
        print("  3. brew install ffmpeg  (macOS)")
        print("  4. 运行登录功能配置 Cookie")

    print()
    return all_passed, results
