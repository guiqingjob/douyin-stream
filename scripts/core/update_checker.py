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

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM video_metadata WHERE uid = ?",
            (uid,),
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


async def _get_remote_video_count(sec_user_id):
    """
    从远程API获取该博主的视频总数

    Args:
        sec_user_id: 用户sec_user_id

    Returns:
        int: 远程视频总数
    """
    try:
        kwargs = _get_f2_kwargs()
        url = f"https://www.douyin.com/user/{sec_user_id}"
        kwargs["url"] = url

        handler = DouyinHandler(kwargs)

        total_count = 0
        page_count = 0

        # 获取所有视频（分页）
        async for aweme_data_list in handler.fetch_user_post_videos(
            sec_user_id, max_counts=float("inf")
        ):
            raw = aweme_data_list._to_raw()
            aweme_list = raw.get("aweme_list", [])
            page_count += len(aweme_list)
            total_count = raw.get("max_cursor", 0)  # 总视频数

            # has_more=0 说明获取完了
            has_more = raw.get("has_more", 0)
            if not has_more:
                break

        # 返回总数
        return total_count if total_count > 0 else page_count

    except Exception as e:
        # 静默失败，返回0
        return 0


async def _check_single_user(user):
    """
    检查单个博主的更新情况

    Returns:
        dict: {
            "uid": str,
            "name": str,
            "remote_count": int,      # 远程总视频数
            "local_count": int,       # 本地已下载数
            "db_count": int,          # 数据库记录数
            "has_update": bool,       # 是否有新视频
            "new_count": int,         # 新视频数量
            "sec_user_id": str,
        }
    """
    uid = user.get("uid")
    name = user.get("nickname", user.get("name", "未知"))
    sec_user_id = user.get("sec_user_id", "")

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

    # 构建 URL
    url = f"https://www.douyin.com/user/{sec_user_id}"

    # 使用 F2 获取远程视频数量
    try:
        kwargs = _get_f2_kwargs()
        kwargs["url"] = url
        handler = DouyinHandler(kwargs)

        # 只获取第一个页面来拿总数
        remote_count = 0
        has_more = 0
        total = 0
        
        async for aweme_data_list in handler.fetch_user_post_videos(
            sec_user_id, max_counts=1
        ):
            raw = aweme_data_list._to_raw()
            
            # 获取视频列表
            aweme_list = raw.get("aweme_list", [])
            remote_count = len(aweme_list) if aweme_list else 0
            
            # 获取分页信息
            total = raw.get("max_cursor", 0)
            has_more = raw.get("has_more", 0)
            
            # 如果有 has_more，说明还有更多视频
            # 但由于我们只获取第一页，这里只能用数据库记录来判断
            break
        
        # 注意：由于我们只获取第一页，无法准确知道远程总数
        # 所以我们使用数据库记录数作为参考（数据库在每次下载时会更新）

    except Exception as e:
        return {
            "uid": uid,
            "name": name,
            "remote_count": db_count,
            "local_count": local_count,
            "db_count": db_count,
            "has_update": False,
            "new_count": 0,
            "sec_user_id": sec_user_id,
            "error": f"检查失败: {e}",
        }

    # 估算新视频数量：数据库数量 - 本地数量
    # 如果远程总数 > 本地数量，则有更新
    new_count = max(0, db_count - local_count) if db_count > local_count else 0

    # 更准确的判断：如果远程能获取到的视频数大于本地数，则有更新
    # 但因为这里我们只快速获取了一页，所以用数据库记录作为参考
    has_update = db_count > local_count

    return {
        "uid": uid,
        "name": name,
        "remote_count": db_count,  # 使用数据库记录作为参考
        "local_count": local_count,
        "db_count": db_count,
        "has_update": has_update,
        "new_count": max(0, db_count - local_count),
        "sec_user_id": sec_user_id,
        "error": None,
    }


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
