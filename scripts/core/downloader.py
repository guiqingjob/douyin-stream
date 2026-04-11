#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频下载模块 - 单个/批量/交互下载（直接调用 F2 API）
"""

import asyncio
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 确保 utils 可以导入
skill_dir = Path(__file__).parent.parent
if str(skill_dir) not in sys.path:
    sys.path.insert(0, str(skill_dir))

import f2
from f2.apps.douyin.db import AsyncUserDB
from f2.apps.douyin.handler import DouyinHandler
from f2.utils.conf_manager import ConfigManager

from .ui import (
    error,
    info,
    print_header,
    print_status,
    success,
    warning,
    ProgressBar,
)
from .config_mgr import get_config
from .following_mgr import list_users

# 导入日志记录器
from utils.logger import logger


def _get_skill_dir():
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent


def _merge_config(main_conf: dict, custom_conf: dict) -> dict:
    """合并配置"""
    result = (main_conf or {}).copy()
    for key, value in (custom_conf or {}).items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key].update(value)
        else:
            result[key] = value
    return result


def _get_f2_kwargs() -> dict:
    """获取 F2 所需的配置参数"""
    config = get_config()

    # 加载 F2 默认配置
    try:
        main_conf_manager = ConfigManager(f2.F2_CONFIG_FILE_PATH)
        all_conf = main_conf_manager.config
        main_conf = all_conf.get("douyin", {}) if all_conf else {}
    except Exception:
        main_conf = {}

    # 加载自定义配置
    custom_conf = {
        "cookie": config.get_cookie(),
        "path": str(config.get_download_path()),
    }

    # 合并配置
    kwargs = _merge_config(main_conf, custom_conf)

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


def _create_video_metadata_table():
    """确保视频元数据表存在"""
    config = get_config()
    db_path = config.get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS video_metadata (
            aweme_id TEXT PRIMARY KEY,
            uid TEXT NOT NULL,
            nickname TEXT,
            desc TEXT,
            create_time INTEGER,
            duration INTEGER,
            digg_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            collect_count INTEGER DEFAULT 0,
            share_count INTEGER DEFAULT 0,
            play_count INTEGER DEFAULT 0,
            local_filename TEXT,
            file_size INTEGER,
            fetch_time INTEGER
        )
    """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_uid ON video_metadata(uid)"
    )

    try:
        cursor.execute("ALTER TABLE video_metadata ADD COLUMN nickname TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def _save_video_metadata_from_raw(raw_data: dict, nickname: str = ""):
    """从原始 API 响应中提取并保存视频统计数据"""
    aweme_list = raw_data.get("aweme_list", [])
    if not aweme_list:
        return 0

    config = get_config()
    db_path = config.get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    fetch_time = int(datetime.now().timestamp())
    saved_count = 0

    for video in aweme_list:
        aweme_id = video.get("aweme_id", "")
        if not aweme_id:
            continue

        stats = video.get("statistics", {}) or {}
        author = video.get("author", {}) or {}
        video_nickname = author.get("nickname", nickname)

        cursor.execute(
            """
            INSERT OR REPLACE INTO video_metadata
            (aweme_id, uid, nickname, desc, create_time, duration,
             digg_count, comment_count, collect_count, share_count, play_count,
             fetch_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                aweme_id,
                author.get("uid", ""),
                video_nickname,
                video.get("desc", ""),
                video.get("create_time", 0),
                video.get("video", {}).get("duration", 0) if video.get("video") else 0,
                stats.get("digg_count", 0),
                stats.get("comment_count", 0),
                stats.get("collect_count", 0),
                stats.get("share_count", 0),
                stats.get("play_count", 0),
                fetch_time,
            ),
        )
        saved_count += 1

    conn.commit()
    conn.close()
    return saved_count


def _reorganize_files(nickname: str, uid: str) -> str:
    """整理文件到下载目录/{博主昵称}/"""
    config = get_config()
    downloads_path = config.get_download_path()
    old_path = downloads_path / "douyin" / "post" / nickname

    if not old_path.exists():
        return None

    # 使用博主昵称作为文件夹名
    folder_name = nickname or uid
    new_path = downloads_path / folder_name
    new_path.mkdir(parents=True, exist_ok=True)

    # 移动文件
    moved_count = 0
    for pattern in ["*.mp4", "*.jpg", "*.webp"]:
        for f in old_path.glob(pattern):
            dest = new_path / f.name
            if not dest.exists():
                shutil.move(str(f), str(dest))
                moved_count += 1

    # 清理旧文件夹
    if old_path.exists():
        try:
            shutil.rmtree(old_path)
        except Exception:
            pass

    if moved_count > 0:
        print(info(f"  [移动] {nickname} -> {folder_name} ({moved_count} 文件)"))

    return folder_name


def _update_last_fetch_time(uid: str, nickname: str = ""):
    """更新 following.json 中的 last_fetch_time"""
    try:
        from utils.following import update_fetch_time

        update_fetch_time(uid, nickname)
        print(info(f"  [更新] last_fetch_time for {nickname or uid}"))
    except ImportError:
        pass


def _sync_following():
    """同步 following.json：从数据库更新用户信息"""
    from utils.following import (
        list_users,
        load_following,
        save_following,
    )

    config = get_config()
    db_path = config.get_db_path()
    downloads_path = config.get_download_path()

    # 加载旧数据
    old_data = load_following()
    old_users = {u.get("uid"): u for u in old_data.get("users", [])}

    new_users_dict = {}  # 用 dict 去重

    # 遍历下载目录找用户
    try:
        folders = list(downloads_path.iterdir())
    except PermissionError as e:
        print(error(f"  [错误] 无法访问下载目录: {e}"))
        return
    except OSError as e:
        print(error(f"  [错误] 文件系统错误: {e}"))
        return

    for folder in folders:
        if not folder.is_dir():
            continue

        folder_name = folder.name

        # 从数据库查找用户
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT uid, sec_user_id, nickname, avatar_url, signature, follower_count, following_count FROM user_info_web WHERE nickname = ? OR uid = ?",
                (folder_name, folder_name),
            )
            user_data = cursor.fetchone()
            conn.close()
        except Exception:
            continue

        if not user_data:
            continue

        uid = str(user_data[0])

        # 如果已经处理过该用户，合并视频数量
        try:
            existing_video_count = new_users_dict[uid].get("video_count", 0)
            new_video_count = len(list(folder.glob("*.mp4")))
            new_users_dict[uid]["video_count"] = max(existing_video_count, new_video_count)
            continue
        except Exception:
            pass

        try:
            video_count = len(list(folder.glob("*.mp4")))
        except (PermissionError, OSError):
            video_count = 0

        # 保留旧数据中的 last_fetch_time
        old_user = old_users.get(uid, {})
        last_fetch = old_user.get("last_fetch_time")

        user_info = {
            "uid": uid,
            "sec_user_id": user_data[1],
            "name": user_data[2],
            "nickname": user_data[2],
            "avatar_url": user_data[3] or "",
            "signature": user_data[4] or "",
            "follower_count": user_data[5] or 0,
            "following_count": user_data[6] or 0,
            "video_count": video_count,
            "last_updated": datetime.now().isoformat(),
            "last_fetch_time": last_fetch,
        }
        new_users_dict[uid] = user_info
        print(info(f"  [同步] {user_data[2]} ({video_count} 视频)"))

    # 保留 following.json 中但目录中没有的用户
    for uid, old_user in old_users.items():
        if uid not in new_users_dict:
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT uid, sec_user_id, nickname, avatar_url, signature, follower_count, following_count FROM user_info_web WHERE uid = ?",
                    (uid,),
                )
                user_data = cursor.fetchone()
                conn.close()

                if user_data:
                    user_info = {
                        "uid": uid,
                        "sec_user_id": user_data[1],
                        "name": user_data[2],
                        "nickname": user_data[2],
                        "avatar_url": user_data[3] or "",
                        "signature": user_data[4] or "",
                        "follower_count": user_data[5] or 0,
                        "following_count": user_data[6] or 0,
                        "video_count": 0,
                        "last_updated": datetime.now().isoformat(),
                        "last_fetch_time": old_user.get("last_fetch_time"),
                    }
                    new_users_dict[uid] = user_info
            except Exception:
                pass

    new_users = list(new_users_dict.values())
    if new_users:
        save_following({"users": new_users})
        print(info(f"\n[同步] following.json 已更新，共 {len(new_users)} 个博主"))


def _generate_data():
    """生成 Web 数据看板"""
    from .data_generator import generate_data

    generate_data()


async def _download_with_stats(url: str, max_counts: int = None):
    """
    使用 F2 API 下载视频并保存统计数据

    Args:
        url: 用户主页 URL
        max_counts: 最大下载数量
    """
    logger.info(f"开始下载: {url}")
    kwargs = _get_f2_kwargs()
    kwargs["url"] = url

    if max_counts:
        kwargs["max_counts"] = max_counts
        logger.info(f"限制下载数量: {max_counts}")

    config = get_config()
    downloads_path = config.get_download_path()

    # 清理临时目录
    f2_temp_path = downloads_path / "douyin"
    if f2_temp_path.exists():
        shutil.rmtree(f2_temp_path)
        logger.info("已清理 F2 临时目录")
        print(info("[清理] F2 临时目录"))

    print(info("[下载] 开始下载..."))
    print(info(f"[路径] {downloads_path}"))
    logger.info(f"下载路径: {downloads_path}")

    # 创建元数据表
    _create_video_metadata_table()

    # 初始化 Handler
    handler = DouyinHandler(kwargs)

    # 解析 sec_user_id
    from f2.apps.douyin.utils import SecUserIdFetcher

    try:
        sec_user_id = await SecUserIdFetcher.get_sec_user_id(url)
    except Exception as e:
        logger.error(f"解析 sec_user_id 失败: {e}")
        print(error("[错误] 无法解析用户 ID"))
        return False

    if not sec_user_id:
        logger.error("无法解析用户 ID")
        print(error("[错误] 无法解析用户 ID"))
        return False

    logger.info(f"sec_user_id: {sec_user_id[:30]}...")
    print(info(f"[信息] sec_user_id: {sec_user_id[:30]}..."))

    # 获取用户信息并保存
    async with AsyncUserDB(str(config.get_db_path())) as db:
        user_path = await handler.get_or_add_user_data(kwargs, sec_user_id, db)

    # 从数据库获取用户信息（昵称）
    conn = sqlite3.connect(str(config.get_db_path()))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uid, nickname FROM user_info_web ORDER BY ROWID DESC LIMIT 1"
    )
    user_info = cursor.fetchone()
    conn.close()

    uid = user_info[0] if user_info else ""
    nickname = user_info[1] if user_info else ""

    if nickname:
        logger.info(f"博主: {nickname} (UID: {uid})")
        print(info(f"[博主] {nickname} (UID: {uid})"))

    # 收集所有视频数据
    total_downloaded = 0
    total_stats_saved = 0

    # 安全限制：默认只下载 10 个视频，防止硬盘被占满
    SAFE_LIMIT = 10
    if max_counts is None:
        max_counts = SAFE_LIMIT
        print(info(f"  ⚠️  安全限制：默认最多下载 {SAFE_LIMIT} 个视频"))
        print(info(f"     如需下载更多，请明确指定数量或使用 '采样下载' 功能"))

    print(info("[下载] 正在获取视频列表..."))
    logger.info(f"正在获取视频列表（上限 {max_counts} 个）...")

    try:
        async for aweme_data_list in handler.fetch_user_post_videos(
            sec_user_id, max_counts=max_counts
        ):
            video_list = aweme_data_list._to_list()

            if video_list:
                # 保存统计数据
                raw_data = aweme_data_list._to_raw()
                stats_saved = _save_video_metadata_from_raw(raw_data, nickname)
                total_stats_saved += stats_saved

                # 创建下载任务
                await handler.downloader.create_download_tasks(
                    kwargs, video_list, user_path
                )

                total_downloaded += len(video_list)
                print(info(f"[下载] 已处理 {total_downloaded} 个视频..."))
                logger.info(f"已处理 {total_downloaded} 个视频")
    except Exception as e:
        logger.error(f"下载过程中出错: {e}")
        print(error(f"下载过程中出错: {e}"))
        # 继续处理已下载的视频

    logger.info(f"保存了 {total_stats_saved} 条视频元数据")
    print(success(f"[统计] 保存了 {total_stats_saved} 条视频元数据"))

    # 整理文件
    print(info("[整理] 重新组织文件..."))
    post_path = downloads_path / "douyin" / "post"
    folder_name = None
    if post_path.exists():
        for folder in post_path.iterdir():
            if folder.is_dir():
                folder_name = _reorganize_files(folder.name, uid)

    # 更新 last_fetch_time
    if folder_name:
        _update_last_fetch_time(uid, nickname or folder_name)

    # 同步 following.json
    print(info("[同步] 更新 following.json..."))
    _sync_following()

    # 生成 Web 数据文件
    print(info("[数据] 生成 Web 数据文件..."))
    _generate_data()

    logger.info(f"下载完成: 共 {total_downloaded} 个视频")
    print(success(f"\n[完成] 共下载 {total_downloaded} 个视频"))
    if folder_name:
        print(info(f"[位置] {downloads_path / folder_name}"))

    return True


def download_by_url_sync(url, max_counts=None):
    """同步包装器：通过 URL 下载单个博主的视频"""
    try:
        # 检查是否已有运行中的事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 如果已有事件循环，创建任务并等待
            import warnings
            warnings.warn(
                "download_by_url_sync called from running event loop. "
                "Consider using the async version directly.",
                RuntimeWarning,
                stacklevel=2
            )
            # 在已有循环中，我们需要用 run_until_complete 的替代方案
            # 但由于无法在同步函数中等待异步，只能抛出异常
            raise RuntimeError(
                "Cannot call sync wrapper from async context. "
                "Use _download_with_stats directly."
            )
        else:
            # 没有运行中的循环，可以安全使用 asyncio.run()
            return asyncio.run(_download_with_stats(url, max_counts))
    except Exception as e:
        print(error(f"下载出错: {e}"))
        return False


def download_by_url(url, max_counts=None):
    """
    通过 URL 下载单个博主的视频

    Args:
        url: 博主主页 URL
        max_counts: 最大下载数量

    Returns:
        是否成功
    """
    print_header("下载博主视频")
    print(info(f"博主 URL: {url}"))
    if max_counts:
        print(info(f"最大下载数量: {max_counts}"))
    print()

    print(info("开始下载..."))
    print()

    result = download_by_url_sync(url, max_counts)

    if result:
        print(success("下载完成！"))
        return True
    else:
        print(error("下载失败，请检查日志"))
        return False


def download_by_uid(uid, max_counts=None):
    """
    通过 UID 下载博主视频

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

    # 构建 URL
    sec_user_id = user.get("sec_user_id", "")
    if sec_user_id and sec_user_id.startswith("MS4w"):
        url = f"https://www.douyin.com/user/{sec_user_id}"
    else:
        url = f"https://www.douyin.com/user/{uid}"

    name = user.get("nickname", user.get("name", "未知"))
    print(info(f"博主: {name} (UID: {uid})"))

    return download_by_url(url, max_counts)


def download_all(auto_confirm=False):
    """
    下载所有关注的博主

    Args:
        auto_confirm: 是否跳过确认

    Returns:
        (success_count, failed_count) 元组
    """
    print_header("全量下载")

    users = list_users()
    if not users:
        print(info("关注列表为空"))
        print(info("请先使用 '添加博主' 功能添加关注"))
        return 0, 0

    print(info(f"共 {len(users)} 位博主"))
    print()

    if not auto_confirm:
        confirm = input("确认开始下载？(y/N): ").strip().lower()
        if confirm != "y":
            print(info("已取消"))
            return 0, 0

    success_count = 0
    failed_count = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        name = user.get("nickname", user.get("name", "未知"))

        print()
        print(info(f"[{i}/{len(users)}] 下载: {name}"))

        ok = download_by_uid(uid)
        if ok:
            success_count += 1
        else:
            failed_count += 1

    print()
    print_header("下载完成")
    print(success(f"成功: {success_count}"))
    print(error(f"失败: {failed_count}"))

    return success_count, failed_count


def interactive_select():
    """
    交互式选择博主下载

    Returns:
        (success_count, failed_count) 元组
    """
    print_header("选择下载")

    users = list_users()
    if not users:
        print(info("关注列表为空"))
        print(info("请先使用 '添加博主' 功能添加关注"))
        return 0, 0

    config = get_config()
    downloads_path = config.get_download_path()

    # 显示用户列表
    print(info("选择要下载的博主（输入序号，逗号分隔，all=全部，q=返回）"))
    print()

    for i, user in enumerate(users, 1):
        uid = user.get("uid", "未知")
        name = user.get("nickname", user.get("name", "未知"))
        folder = user.get("folder", name or uid)
        user_dir = downloads_path / folder
        local_count = len(list(user_dir.glob("*.mp4"))) if user_dir.exists() else 0

        status = f"已下载 {local_count} 个" if local_count > 0 else "未下载"
        print(f"  {i:2}. {name} ({status})")

    print()
    choice = input("请选择: ").strip().lower()

    if choice == "q" or not choice:
        print(info("已取消"))
        return 0, 0

    if choice == "all":
        return download_all(auto_confirm=True)

    # 解析选择
    try:
        indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
        selected = []
        for idx in indices:
            if 1 <= idx <= len(users):
                selected.append(users[idx - 1])
            else:
                print(warning(f"无效的序号: {idx}"))

        if not selected:
            print(error("没有有效的选择"))
            return 0, 0

        print()
        print(info(f"已选择 {len(selected)} 个博主"))

        success_count = 0
        failed_count = 0

        for i, user in enumerate(selected, 1):
            uid = user.get("uid")
            name = user.get("nickname", user.get("name", "未知"))

            print()
            print(info(f"[{i}/{len(selected)}] 下载: {name}"))

            ok = download_by_uid(uid)
            if ok:
                success_count += 1
            else:
                failed_count += 1

        print()
        print(success(f"下载完成: 成功 {success_count}，失败 {failed_count}"))
        return success_count, failed_count

    except ValueError:
        print(error("无效的输入，请输入数字"))
        return 0, 0


def download_sample(auto_confirm=False):
    """
    采样下载：每个博主只下载1个视频，用于快速更新统计数据

    Args:
        auto_confirm: 是否跳过确认

    Returns:
        (success_count, failed_count) 元组
    """
    print_header("采样下载")

    users = list_users()
    if not users:
        print(info("关注列表为空"))
        return 0, 0

    print(info(f"每个博主只下载 1 个视频"))
    print(info(f"共 {len(users)} 位博主"))
    print()

    if not auto_confirm:
        confirm = input("确认开始？(y/N): ").strip().lower()
        if confirm != "y":
            print(info("已取消"))
            return 0, 0

    success_count = 0
    failed_count = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        name = user.get("nickname", user.get("name", "未知"))

        print(info(f"[{i}/{len(users)}] 采样: {name}"))

        ok = download_by_uid(uid, max_counts=1)
        if ok:
            success_count += 1
        else:
            failed_count += 1

    print()
    print(success(f"采样完成: 成功 {success_count}，失败 {failed_count}"))
    return success_count, failed_count
