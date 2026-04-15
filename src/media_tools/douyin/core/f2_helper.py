#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F2 辅助模块 - 统一管理 F2 配置和初始化
"""

import f2
import sqlite3
from f2.utils.conf_manager import ConfigManager

from .config_mgr import get_config


def _disable_f2_bark_notifications() -> None:
    """关闭 F2 的 Bark 推送，避免无关网络请求和噪音日志。"""
    try:
        from f2.apps.bark.utils import ClientConfManager as BarkClientConfManager

        BarkClientConfManager.enable_bark = classmethod(lambda cls: False)
    except Exception:
        pass


_disable_f2_bark_notifications()


def _get_active_douyin_cookie_from_pool(db_path) -> str:
    """从账号池里取一个当前可用的抖音 Cookie 作为兜底。"""
    try:
        with sqlite3.connect(str(db_path), timeout=15.0) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Accounts_Pool (
                    account_id TEXT PRIMARY KEY,
                    platform TEXT,
                    cookie_data TEXT,
                    status TEXT DEFAULT 'active',
                    last_used TIMESTAMP,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                SELECT cookie_data
                FROM Accounts_Pool
                WHERE platform = 'douyin' AND status = 'active' AND cookie_data IS NOT NULL AND cookie_data != ''
                ORDER BY
                    CASE WHEN last_used IS NULL THEN 1 ELSE 0 END,
                    last_used DESC,
                    create_time ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row and row[0] else ""
    except Exception:
        return ""


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
    cookie = config.get_cookie()
    if not cookie:
        cookie = _get_active_douyin_cookie_from_pool(config.get_db_path())

    # 加载 F2 默认配置
    try:
        main_conf_manager = ConfigManager(f2.F2_CONFIG_FILE_PATH)
        all_conf = main_conf_manager.config
        main_conf = all_conf.get("douyin", {}) if all_conf else {}
    except Exception:
        main_conf = {}

    # 自定义配置
    custom_conf = {
        "cookie": cookie,
        "path": str(config.get_download_path()),
    }

    # 合并配置
    kwargs = merge_f2_config(main_conf, custom_conf)

    # 添加必要参数
    kwargs["app_name"] = "douyin"
    kwargs["mode"] = "post"
    kwargs["path"] = str(config.get_download_path())

    # 让 F2 生成更短的临时文件名，避免超长标题在下载阶段触发路径问题。
    # 最终展示名会在本地重命名流程里恢复为可读标题。
    kwargs["naming"] = "{aweme_id}"

    # 显式使用全量抓取，避免 F2 打印“未提供日期区间参数”并误触发日期过滤。
    kwargs["interval"] = kwargs.get("interval") or "all"

    # 默认略微放宽超时时间，减少 HEAD/GET 抖动导致的误报失败。
    try:
        current_timeout = int(kwargs.get("timeout") or 0)
    except (TypeError, ValueError):
        current_timeout = 0
    kwargs["timeout"] = max(current_timeout, 20)

    # 确保 headers 存在
    if not kwargs.get("headers"):
        kwargs["headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.douyin.com/",
        }

    return kwargs
