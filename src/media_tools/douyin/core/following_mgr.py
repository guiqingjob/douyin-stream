
from media_tools.logger import get_logger
logger = get_logger(__name__)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关注列表管理模块 - 增删查取关清理
"""

import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .ui import (
    bold,
    error,
    format_number,
    info,
    print_header,
    print_status,
    print_table,
    separator,
    success,
    warning,
)
from .config_mgr import get_config


def _get_skill_dir():
    """获取项目根目录"""
    return get_config().project_root


def list_users():
    """
    列出所有关注的博主 (从 SQLite V2 架构读取)

    Returns:
        用户列表 (List of dicts)
    """
    config = get_config()
    db_path = config.get_db_path()
    
    users = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT uid, sec_user_id, nickname, platform, sync_status, last_fetch_time FROM creators ORDER BY last_fetch_time DESC")
            
            for row in cursor.fetchall():
                users.append({
                    "uid": row["uid"],
                    "sec_user_id": row["sec_user_id"],
                    "nickname": row["nickname"] or row["uid"],
                    "name": row["nickname"] or row["uid"],
                    "platform": row["platform"],
                    "sync_status": row["sync_status"],
                    "last_fetch_time": row["last_fetch_time"]
                })
    except Exception as e:
        logger.error(f"读取关注列表失败: {e}")
        
    return users


def get_user(uid: str):
    config = get_config()
    db_path = config.get_db_path()
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT uid, sec_user_id, nickname, platform, sync_status, last_fetch_time FROM creators WHERE uid = ?",
                (uid,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "uid": row["uid"],
                "sec_user_id": row["sec_user_id"],
                "nickname": row["nickname"] or row["uid"],
                "name": row["nickname"] or row["uid"],
                "platform": row["platform"],
                "sync_status": row["sync_status"],
                "last_fetch_time": row["last_fetch_time"],
            }
    except Exception as e:
        logger.error(f"读取用户失败: {e}")
        return None


def add_user(url):
    """
    通过主页链接添加用户 (写入 SQLite V2 架构)

    Args:
        url: 抖音主页链接

    Returns:
        (success, user_info) 元组
    """
    print_header("添加关注博主")

    # 从 URL 提取 sec_user_id
    sec_match = re.search(r'/user/(MS4wLjABAAAA[^/"\s?]+)', url)
    if not sec_match:
        logger.info(error("无法从 URL 提取用户标识"))
        logger.info(info("请使用抖音主页链接，格式如:"))
        logger.info(info("https://www.douyin.com/user/MS4wLjABAAAA..."))
        return False, None

    sec_user_id = sec_match.group(1)

    # 检查是否已存在
    config = get_config()
    db_path = config.get_db_path()
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uid, nickname FROM creators WHERE sec_user_id = ?", (sec_user_id,))
            row = cursor.fetchone()
            if row:
                name = row[1] or "未知"
                logger.info(warning(f"用户已在关注列表: {name} (UID: {row[0]})"))
                return False, {"uid": row[0], "sec_user_id": sec_user_id, "nickname": name}
    except Exception as e:
        logger.error(f"查询数据库失败: {e}")

    # 通过 F2 获取用户信息
    logger.info(info("正在通过 F2 获取用户信息..."))
    user_info = _fetch_user_info_via_f2(url, sec_user_id)

    if not user_info:
        logger.info(error("获取用户信息失败"))
        return False, None

    uid = user_info.get("uid")
    nickname = user_info.get("nickname", "")
    
    # 写入数据库 (代替旧版的 following.json)
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO creators 
                (uid, sec_user_id, nickname, platform, sync_status, last_fetch_time)
                VALUES (?, ?, ?, 'douyin', 'active', ?)
            """, (uid, sec_user_id, nickname, now))
            conn.commit()
    except Exception as e:
        logger.error(f"保存用户到数据库失败: {e}")
        return False, None

    logger.info(success(f"已添加用户: {nickname} (UID: {uid})"))
    logger.info(info("提示: 运行下载功能可获取完整用户信息和视频"))

    return True, user_info


def _fetch_user_info_via_f2(url, sec_user_id):
    """
    通过 F2 下载1个视频来获取用户信息

    Args:
        url: 用户主页 URL
        sec_user_id: 用户 sec_user_id

    Returns:
        用户信息字典
    """
    config = get_config()
    downloads_path = config.get_download_path()
    skill_dir = _get_skill_dir()

    # 清理旧的 F2 临时目录
    f2_temp_path = downloads_path / "douyin"
    if f2_temp_path.exists():
        import shutil

        shutil.rmtree(f2_temp_path)

    # 运行 F2 下载
    cookie = config.get_cookie()
    f2_args = [
        sys.executable,
        "-m",
        "f2",
        "dy",
        "-u",
        url,
        "-M",
        "post",
        "--max-counts",
        "1",
        "-p",
        str(downloads_path),
    ]

    if cookie:
        f2_args.extend(["-k", cookie])

    result = subprocess.run(
        f2_args,
        capture_output=True,
        text=True,
        cwd=str(skill_dir),
    )

    if result.returncode != 0:
        logger.info(error(f"F2 下载失败: {result.stderr}"))
        return None

    # 从数据库读取用户信息
    db_path = config.get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT uid, sec_user_id, nickname, avatar_url, signature,
                   follower_count, following_count, aweme_count
            FROM user_info_web WHERE sec_user_id = ?
            ORDER BY ROWID DESC LIMIT 1
        """,
            (sec_user_id,),
        )

        row = cursor.fetchone()

        if not row:
            logger.info(error("数据库中未找到用户信息"))
            return None

        # 归档视频文件
        numeric_uid = str(row[0])
        post_path = downloads_path / "douyin" / "post"
        if post_path.exists():
            import shutil

            for folder in post_path.iterdir():
                if folder.is_dir():
                    target_dir = downloads_path / numeric_uid
                    target_dir.mkdir(parents=True, exist_ok=True)
                    for f in folder.glob("*.mp4"):
                        dest = target_dir / f.name
                        if not dest.exists():
                            shutil.move(str(f), str(dest))
                    for f in folder.glob("*.jpg"):
                        dest = target_dir / f.name
                        if not dest.exists():
                            shutil.move(str(f), str(dest))
                    try:
                        shutil.rmtree(folder)
                    except Exception:
                        pass

        return {
            "uid": numeric_uid,
            "sec_user_id": row[1] or "",
            "name": _clean_nickname(row[2] or ""),
            "nickname": _clean_nickname(row[2] or ""),
            "avatar_url": row[3] or "",
            "signature": row[4] or "",
            "follower_count": row[5] or 0,
            "following_count": row[6] or 0,
            "video_count": row[7] or 0,
            "last_updated": datetime.now().isoformat(),
            "last_fetch_time": None,
        }

    except Exception as e:
        logger.info(error(f"数据库读取失败: {e}"))
        return None
    finally:
        if conn:
            conn.close()


def _clean_nickname(name):
    """清理昵称"""
    if not name:
        return ""
    suffixes = ["的抖音", "的Douyin", " - 抖音", " - Douyin", " | 抖音", " | Douyin"]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.strip()


def remove_user(uid, delete_local=False):
    """
    移除关注的博主 (从 SQLite V2 架构)

    Args:
        uid: 用户 UID
        delete_local: 是否删除本地视频文件

    Returns:
        是否成功
    """
    config = get_config()
    db_path = config.get_db_path()
    
    # 获取用户信息
    name = str(uid)
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nickname FROM creators WHERE uid = ?", (uid,))
            row = cursor.fetchone()
            if not row:
                logger.info(error(f"用户 {uid} 不在关注列表中"))
                return False
            name = row[0] or str(uid)
            
            # 删除关注记录
            cursor.execute("DELETE FROM creators WHERE uid = ?", (uid,))
            
            # 清理旧数据库遗留记录 (兼容旧代码清理)
            cursor.execute("DELETE FROM user_info_web WHERE uid = ?", (uid,))
            cursor.execute("DELETE FROM video_metadata WHERE uid = ? OR nickname = ?", (uid, name))
            conn.commit()
            
            logger.info(success(f"已从关注列表移除: {name} (UID: {uid})"))
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return False

    # 删除本地视频文件
    if delete_local:
        downloads_path = config.get_download_path()
        user_dir = downloads_path / name
        if not user_dir.exists():
            user_dir = downloads_path / str(uid)

        if user_dir.exists():
            import shutil
            try:
                shutil.rmtree(user_dir)
                logger.info(success(f"已删除本地视频文件: {user_dir}"))
                
                # 同步删除 media_assets 记录
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM media_assets WHERE creator_uid = ?", (uid,))
                    conn.commit()
            except Exception as e:
                logger.info(error(f"删除本地文件夹失败: {e}"))
        else:
            logger.info(info("本地无该用户视频目录"))

    return True


def display_users():
    """显示关注列表"""
    print_header("关注列表")

    users = list_users()
    if not users:
        logger.info(info("关注列表为空"))
        logger.info(info("请先使用 '添加博主' 功能添加关注"))
        return []

    config = get_config()
    downloads_path = config.get_download_path()

    headers = ["序号", "昵称", "UID", "粉丝", "视频", "本地视频", "最后获取"]
    rows = []

    for i, user in enumerate(users, 1):
        uid = user.get("uid", "未知")
        name = user.get("nickname", user.get("name", "未知"))
        followers = format_number(user.get("follower_count", 0))
        videos = user.get("video_count", 0)
        last_fetch = user.get("last_fetch_time", "未获取")

        # 检查本地视频
        folder = user.get("folder", name or uid)
        user_dir = downloads_path / folder
        local_count = len(list(user_dir.glob("*.mp4"))) if user_dir.exists() else 0

        rows.append([i, name, uid, followers, videos, local_count, last_fetch])

    print_table(headers, rows)
    logger.info()
    logger.info(info(f"共 {len(users)} 位博主"))

    return users


def batch_add_urls(urls):
    """
    批量添加用户 URL

    Args:
        urls: URL 列表

    Returns:
        (added, updated, failed) 计数
    """
    print_header("批量添加博主")

    added = 0
    updated = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        logger.info(info(f"[{i}/{len(urls)}] 处理: {url[:50]}..."))
        ok, user_info = add_user(url)
        if ok:
            added += 1
        elif user_info:
            # 用户已存在，计为更新
            updated += 1
        else:
            failed += 1

    logger.info()
    logger.info(success(f"完成! 新增 {added} 个，已存在 {updated} 个，失败 {failed} 个"))
    return added, updated, failed
