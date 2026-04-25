#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F2 辅助模块 - 统一管理 F2 配置和初始化
"""

import f2
import logging
import sqlite3

logger = logging.getLogger(__name__)
from f2.utils.conf_manager import ConfigManager

from .config_mgr import get_config


def _disable_f2_bark_notifications() -> None:
    """关闭 F2 的 Bark 推送，避免无关网络请求和噪音日志。"""
    try:
        from f2.apps.bark.utils import ClientConfManager as BarkClientConfManager

        BarkClientConfManager.enable_bark = classmethod(lambda cls: False)
    except (ImportError, ModuleNotFoundError, AttributeError):
        pass


_disable_f2_bark_notifications()


def _get_active_douyin_cookie_from_pool(db_path) -> str:
    """从账号池里取一个当前可用的抖音 Cookie（轮换策略：最久未使用优先）。

    取到后自动更新 last_used，实现 round-robin。
    """
    try:
        from media_tools.db.core import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 最久未使用的排前面（NULL 即从未使用，最优先）
            cursor.execute("""
                SELECT account_id, cookie_data
                FROM Accounts_Pool
                WHERE platform = 'douyin' AND status = 'active' AND cookie_data IS NOT NULL AND cookie_data != ''
                ORDER BY
                    CASE WHEN last_used IS NULL THEN 0 ELSE 1 END,
                    last_used ASC,
                    create_time ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row and row[1]:
                # 更新 last_used 实现轮换
                cursor.execute(
                    "UPDATE Accounts_Pool SET last_used = CURRENT_TIMESTAMP WHERE account_id = ?",
                    (row[0],)
                )
                conn.commit()
                return row[1]
            return ""
    except sqlite3.Error as e:
        logger.debug(f"读取F2数据库值失败: {e}")
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

    # 优先使用账号池（支持多账号轮换），config.yaml cookie 作为兜底
    cookie = ""
    get_db_path = getattr(config, "get_db_path", None)
    if callable(get_db_path):
        cookie = _get_active_douyin_cookie_from_pool(get_db_path())
    if not cookie:
        cookie = config.get_cookie()

    # 加载 F2 默认配置
    try:
        main_conf_manager = ConfigManager(f2.F2_CONFIG_FILE_PATH)
        all_conf = main_conf_manager.config
        main_conf = all_conf.get("douyin", {}) if all_conf else {}
    except (OSError, KeyError, TypeError):
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
