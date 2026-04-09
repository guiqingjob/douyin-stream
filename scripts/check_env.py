#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检测脚本 - 检查 Python 版本和依赖
"""
import subprocess
import sys

from utils.logger import logger


def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    logger.info(f"当前 Python 版本: {version.major}.{version.minor}.{version.micro}")

    # f2 支持 Python 3.9 - 3.13
    if version.major == 3 and version.minor <= 13:
        logger.info("✓ Python 版本兼容 (3.9-3.13)")
        return True
    else:
        print(
            f"✗ Python 版本不兼容: f2 需要 Python 3.9-3.13，当前是 {version.major}.{version.minor}"
        )
        logger.info("  解决方案: 使用 pyenv 或 conda 安装 Python 3.11")
        return False


def check_f2():
    """检查 f2 是否安装"""
    try:
        result = subprocess.run(["pip", "show", "f2"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    logger.info(f"✓ f2 已安装: {line.split(':')[1].strip()}")
                    return True
        logger.info("✗ f2 未安装")
        return False
    except Exception as e:
        logger.info(f"✗ 检查 f2 失败: {e}")
        return False


def check_playwright():
    """检查 playwright 是否安装"""
    try:
        result = subprocess.run(
            ["pip", "show", "playwright"], capture_output=True, text=True
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    logger.info(f"✓ playwright 已安装: {line.split(':')[1].strip()}")
                    return True
        logger.info("✗ playwright 未安装")
        return False
    except Exception as e:
        logger.info(f"✗ 检查 playwright 失败: {e}")
        return False


def main():
    logger.info("=" * 50)
    logger.info("抖音批量下载技能 - 环境检测")
    logger.info("=" * 50)

    checks = [
        ("Python 版本", check_python_version()),
        ("f2", check_f2()),
        ("playwright", check_playwright()),
    ]

    logger.info("=" * 50)
    logger.info("检测结果:")
    for name, result in checks:
        status = "✓" if result else "✗"
        logger.info(f"  {status} {name}")

    if all(r for _, r in checks):
        logger.info("\n✓ 环境检测通过，可以正常使用!")
        return 0
    else:
        logger.info("\n✗ 环境检测未通过，请先配置环境")
        return 1


if __name__ == "__main__":
    sys.exit(main())
