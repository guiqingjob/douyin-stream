#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新检查模块 - 快速检查已关注博主是否有新视频（不下载）
"""

import asyncio
import sqlite3
import sys
from pathlib import Path

# 确保 utils 可以导入
skill_dir = Path(__file__).parent.parent
if str(skill_dir) not in sys.path:
    sys.path.insert(0, str(skill_dir))

import f2
from f2.apps.douyin.handler import DouyinHandler
from f2.utils.conf_manager import ConfigManager

from .ui import (
    bold,
    dim,
    error,
    format_number,
    info,
    print_header,
    print_status,
    separator,
    success,
    warning,
)
from .config_mgr import get_config
from .following_mgr import list_users


def _get_f2_kwargs():
    """获取 F2 所需的配置参数"""
    config = get_config()

    try:
        main_conf_manager = ConfigManager(f2.F2_CONFIG_FILE_PATH)
        all_conf = main_conf_manager.config
        main_conf = all_conf.get("douyin", {}) if all_conf else {}
    except Exception:
        main_conf = {}

    custom_conf = {
        "cookie": config.get_cookie(),
        "path": str(config.get_download_path()),
    }

    kwargs = _merge_config(main_conf, custom_conf)
    kwargs["app_name"] = "douyin"
    kwargs["mode"] = "post"
    kwargs["path"] = str(config.get_download_path())

    if not kwargs.get("headers"):
        kwargs["headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.douyin.com/",
        }

    return kwargs


def _merge_config(main_conf: dict, custom_conf: dict) -> dict:
    """合并配置"""
    result = (main_conf or {}).copy()
    for key, value in (custom_conf or {}).items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key].update(value)
        else:
            result[key] = value
    return result


def _get_local_video_count(uid, user_info):
    """获取本地已下载的视频数量"""
    config = get_config()
    downloads_path = config.get_download_path()

    folder = user_info.get("folder") or user_info.get("nickname") or str(uid)
    user_dir = downloads_path / folder
    if user_dir.exists():
        return len(list(user_dir.glob("*.mp4")))
    return 0


def _get_db_video_count(uid):
    """从数据库获取该用户的视频元数据数量"""
    config = get_config()
    db_path = config.get_db_path()

    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM video_metadata WHERE uid = ?",
            (uid,),
        )
        count = cursor.fetchone()[0]
        return count
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()


async def _get_remote_video_count(sec_user_id):
    """
    从远程API获取该博主的视频总数
    
    后台静默模式：只获取最新 20 个视频来判断是否有更新
    完全抑制所有输出
    
    Args:
        sec_user_id: 用户sec_user_id
    
    Returns:
        int: 远程视频总数
    """
    import logging
    import os

    # 初始化变量，确保finally中可以安全访问
    old_stdout = None
    old_stderr = None
    devnull = None

    try:
        # 完全抑制输出
        old_stdout = os.dup(1)
        old_stderr = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        logging.disable(logging.CRITICAL)

        kwargs = _get_f2_kwargs()
        url = f"https://www.douyin.com/user/{sec_user_id}"
        kwargs["url"] = url

        handler = DouyinHandler(kwargs)

        video_count = 0

        # 只获取最新 1 页
        async for aweme_data_list in handler.fetch_user_post_videos(
            sec_user_id, max_counts=20
        ):
            raw = aweme_data_list._to_raw()
            aweme_list = raw.get("aweme_list", [])
            video_count += len(aweme_list)
            break

        return video_count

    except Exception as e:
        return 0
    finally:
        # 恢复输出
        try:
            if old_stdout is not None:
                os.dup2(old_stdout, 1)
                os.close(old_stdout)
            if old_stderr is not None:
                os.dup2(old_stderr, 2)
                os.close(old_stderr)
            if devnull is not None:
                os.close(devnull)
            logging.disable(logging.NOTSET)
        except Exception:
            pass


async def _check_single_user(user):
    """
    检查单个博主的更新情况（后台静默模式）
    
    Returns:
        dict: 检查结果
    """
    import logging
    import os
    
    uid = user.get("uid")
    name = user.get("nickname", user.get("name", "未知"))
    sec_user_id = user.get("sec_user_id", "")

    # 完全抑制 F2 的输出
    old_stdout = os.dup(1)
    old_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    logging.disable(logging.CRITICAL)

    try:
        local_count = _get_local_video_count(uid, user)
        db_count = _get_db_video_count(uid)

        if not sec_user_id:
            return {
                "uid": uid,
                "name": name,
                "remote_count": db_count,
                "local_count": local_count,
                "db_count": db_count,
                "has_update": False,
                "new_count": 0,
                "sec_user_id": "",
                "error": "缺少 sec_user_id",
            }

        # 获取远程视频数（只取最新 20 个）
        kwargs = _get_f2_kwargs()
        url = f"https://www.douyin.com/user/{sec_user_id}"
        kwargs["url"] = url
        handler = DouyinHandler(kwargs)

        remote_count = 0
        async for aweme_data_list in handler.fetch_user_post_videos(
            sec_user_id, max_counts=20
        ):
            raw = aweme_data_list._to_raw()
            aweme_list = raw.get("aweme_list", [])
            remote_count += len(aweme_list)
            break  # 只取一页

        # 计算新视频数
        if remote_count > local_count:
            has_update = True
            new_count = remote_count - local_count
        else:
            has_update = False
            new_count = 0

        return {
            "uid": uid,
            "name": name,
            "remote_count": remote_count,
            "local_count": local_count,
            "db_count": db_count,
            "has_update": has_update,
            "new_count": new_count,
            "sec_user_id": sec_user_id,
        }
    finally:
        # 恢复输出
        os.dup2(old_stdout, 1)
        os.dup2(old_stderr, 2)
        os.close(devnull)
        logging.disable(logging.NOTSET)


def check_all_updates():
    """
    检查所有已关注博主的更新情况

    Returns:
        dict: {
            "users": list,           # 每个用户的检查结果
            "total_new": int,        # 总新视频数
            "has_updates_count": int, # 有更新的博主数
            "total_users": int,      # 总检查的博主数
        }
    """
    print_header("🔍 检查博主更新")

    users = list_users()
    if not users:
        print(info("关注列表为空"))
        return {
            "users": [],
            "total_new": 0,
            "has_updates_count": 0,
            "total_users": 0,
        }

    print(info(f"正在检查 {len(users)} 位博主...\n"))

    results = []
    total_new = 0
    has_updates_count = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        name = user.get("nickname", user.get("name", "未知"))
        local_count = _get_local_video_count(uid, user)
        db_count = _get_db_video_count(uid)
        sec_user_id = user.get("sec_user_id", "")

        # 优先使用远程API检查更新
        remote_count = None
        if sec_user_id:
            try:
                # 异步调用获取远程视频数量
                import asyncio
                remote_count = asyncio.run(_get_remote_video_count(sec_user_id))
            except Exception:
                # 如果远程检查失败，降级使用数据库记录
                remote_count = db_count
        else:
            remote_count = db_count

        # 计算新视频数：远程数量 - 本地数量
        if remote_count and remote_count > local_count:
            new_count = remote_count - local_count
            has_update = True
        else:
            new_count = 0
            has_update = False

        if has_update:
            total_new += new_count
            has_updates_count += 1
            status_icon = "🆕"
            status_text = f"有 {new_count} 个新视频"
        else:
            status_icon = "✓"
            status_text = "已是最新"

        print(f"  {status_icon} {name}")
        print(f"     本地: {local_count} 个 | 远程: {remote_count} 个 | {status_text}")
        print()

        results.append({
            "uid": uid,
            "name": name,
            "local_count": local_count,
            "remote_count": remote_count,
            "db_count": db_count,
            "has_update": has_update,
            "new_count": new_count,
        })

    # 汇总
    print(separator("─", 60))
    print()
    print(bold(f"📊 检查结果:"))
    print(f"  检查博主: {len(users)} 位")
    print(f"  有更新: {bold(str(has_updates_count))} 位")
    print(f"  新视频: {bold(str(total_new))} 个")
    print()

    return {
        "users": results,
        "total_new": total_new,
        "has_updates_count": has_updates_count,
        "total_users": len(users),
    }


def download_updates_for_user(uid, max_counts=None):
    """
    下载指定博主的更新

    Args:
        uid: 用户 UID
        max_counts: 最大下载数量

    Returns:
        是否成功
    """
    from utils.following import get_user

    user = get_user(uid)
    if not user:
        print(error(f"用户 {uid} 不在关注列表中"))
        return False

    sec_user_id = user.get("sec_user_id", "")
    if sec_user_id and sec_user_id.startswith("MS4w"):
        url = f"https://www.douyin.com/user/{sec_user_id}"
    else:
        url = f"https://www.douyin.com/user/{uid}"

    name = user.get("nickname", user.get("name", "未知"))
    print(info(f"下载更新: {name}"))

    from .downloader import download_by_url

    return download_by_url(url, max_counts)
