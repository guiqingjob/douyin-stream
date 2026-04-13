#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F2 辅助模块 - 统一管理 F2 配置和初始化
"""

import f2
from f2.utils.conf_manager import ConfigManager

from .config_mgr import get_config


def merge_f2_config(main_conf: dict, custom_conf: dict) -> dict:
    """
    合并 F2 配置

    Args:
        main_conf: F2 默认配置
        custom_conf: 自定义配置

    Returns:
        合并后的配置
    """
    result = (main_conf or {}).copy()
    for key, value in (custom_conf or {}).items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key].update(value)
        else:
            result[key] = value
    return result


def get_f2_kwargs() -> dict:
    """
    获取 F2 所需的配置参数

    Returns:
        F2 配置字典
    """
    config = get_config()

    # 加载 F2 默认配置
    try:
        main_conf_manager = ConfigManager(f2.F2_CONFIG_FILE_PATH)
        all_conf = main_conf_manager.config
        main_conf = all_conf.get("douyin", {}) if all_conf else {}
    except Exception:
        main_conf = {}

    # 自定义配置
    custom_conf = {
        "cookie": config.get_cookie(),
        "path": str(config.get_download_path()),
    }

    # 合并配置
    kwargs = merge_f2_config(main_conf, custom_conf)

    # 添加必要参数
    kwargs["app_name"] = "douyin"
    kwargs["mode"] = "post"
    kwargs["path"] = str(config.get_download_path())

    # 确保 headers 存在
    if not kwargs.get("headers"):
        kwargs["headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.douyin.com/",
        }

    return kwargs
