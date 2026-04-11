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


def _clean_video_title(raw_title: str) -> str:
    """清洗视频标题：去掉换行符和 #话题标签，并智能截断长标题"""
    # 1. 按换行分割，取第一行（正文）
    main_part = raw_title.replace('<br>', '\n').split('\n')[0]
    
    # 2. 截取第一个 # 之前的内容
    if '#' in main_part:
        clean = main_part[:main_part.index('#')].strip()
    else:
        clean = main_part.strip()
    
    # 3. 智能截断：限制到 40 字以内，保持核心语义
    if len(clean) > 40:
        # 优先在句末标点（？ ！ 。）截断
        for p in ['？', '！', '。']:
            idx = clean.find(p)
            if 10 < idx < 50:
                return clean[:idx + 1].strip()
        
        # 其次在空格处截断（适合长标题中的短语）
        space_idx = clean.find(' ')
        if space_idx > 15:
            return clean[:space_idx].strip()
            
        # 再次在逗号处截断（适合长句子）
        comma_idx = clean.find('，')
        if comma_idx > 10:
            return clean[:comma_idx + 1].strip()
        
        # 如果都没有，强制截断
        return clean[:35] + '...'
        
    return clean


def _rename_videos_in_downloads(nickname: str, uid: str, downloads_path: Path) -> str:
    """重命名下载目录下的视频文件（包括已在目标子目录的情况）"""
    import re
    import sqlite3
    
    config = get_config()
    db_path = config.get_db_path()
    
    # 博主文件夹
    folder_name = nickname or uid
    user_dir = downloads_path / folder_name
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # 连接数据库获取该博主最近的视频标题
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 查询该博主最近下载的视频标题
    cursor.execute(
        "SELECT aweme_id, desc FROM video_metadata WHERE uid = ? ORDER BY fetch_time DESC LIMIT 10",
        (uid,)
    )
    recent_videos = cursor.fetchall()
    
    if not recent_videos:
        conn.close()
        return None
    
    # 构建 aweme_id -> 标题 映射
    title_map = {row[0]: row[1] for row in recent_videos}
    
    renamed_count = 0
    processed_count = 0
    
    # 递归查找下载目录下的所有视频文件
    for f in downloads_path.rglob("*.mp4"):
        # 跳过 douyin/post 临时目录
        if "/douyin/post/" in str(f):
            continue
            
        stem = f.stem
        
        # 方法1：尝试从文件名提取 aweme_id
        aweme_id = None
        for vid in title_map.keys():
            if vid in stem:
                aweme_id = vid
                break
        
        # 方法2：如果文件名不包含 aweme_id，使用标题关键词匹配
        if not aweme_id:
            for vid, title in title_map.items():
                # 提取标题中的中文关键词
                clean_title = _clean_video_title(title)
                # 检查标题中的连续中文是否出现在文件名中
                chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', clean_title)
                for word in chinese_words[:3]:  # 取前3个关键词
                    if word in stem:
                        aweme_id = vid
                        break
                if aweme_id:
                    break
        
        if aweme_id and aweme_id in title_map:
            title = title_map[aweme_id]
            clean_title = _clean_video_title(title)
            clean_title = re.sub(r'[<>:"/\\|?*]', '', clean_title).strip()
            if len(clean_title) > 60:
                clean_title = clean_title[:60]
            
            new_name = f"{clean_title}{f.suffix}"
            dest = user_dir / new_name
            
            # 如果文件名已经是清洗后的（与新名相同），跳过
            if f.name == new_name and f.parent == user_dir:
                continue
            
            if not dest.exists():
                shutil.move(str(f), str(dest))
                processed_count += 1
                renamed_count += 1
                print(info(f"  [重命名] {f.name[:40]}... → {new_name[:40]}..."))
            else:
                counter = 1
                while dest.exists():
                    new_name = f"{clean_title}_{counter}{f.suffix}"
                    dest = user_dir / new_name
                    counter += 1
                shutil.move(str(f), str(dest))
                processed_count += 1
                renamed_count += 1
        else:
            # 无法匹配，直接移动到目标目录
            if f.parent != user_dir:
                dest = user_dir / f.name
                if not dest.exists():
                    shutil.move(str(f), str(dest))
                    processed_count += 1

    if processed_count > 0:
        print(info(f"  [整理] 已处理 {processed_count} 个文件到 {folder_name}/（{renamed_count} 个已重命名）"))
        
        # 更新数据库中的 local_filename 字段
        cursor.execute(
            "UPDATE video_metadata SET local_filename = ? WHERE uid = ?",
            (folder_name, uid)
        )
        conn.commit()
        print(info(f"  [更新] 已更新 {folder_name} 的 local_filename"))

    conn.close()

    return folder_name


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

    # 移动文件（文件名已经在下载时清洗过，无需重命名）
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

    # 从数据库获取用户信息（通过 sec_user_id 查找）
    conn = sqlite3.connect(str(config.get_db_path()))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uid, nickname FROM user_info_web WHERE sec_user_id LIKE ? LIMIT 1",
        (f"{sec_user_id[:20]}%",)
    )
    user_info = cursor.fetchone()
    conn.close()
    
    # 如果没找到，使用最新记录（向后兼容）
    if not user_info:
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

    # 统计本地已有视频（增量下载）
    existing_videos = set()
    if user_path.exists():
        existing_videos = {f.stem for f in user_path.glob("*.mp4")}
        if existing_videos:
            print(info(f"[本地] 已有 {len(existing_videos)} 个视频文件，将跳过已下载的"))

    # 同时从数据库获取已下载的视频 ID（防止文件被删除后重复下载）
    config = get_config()
    db_path = config.get_db_path()
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT aweme_id FROM video_metadata WHERE uid = ? AND aweme_id != ''",
            (uid,)
        )
        db_videos = {row[0] for row in cursor.fetchall() if row[0]}
        conn.close()
        
        if db_videos:
            # 合并本地文件和数据库记录
            new_from_db = db_videos - existing_videos
            if new_from_db:
                print(info(f"[数据库] 发现 {len(new_from_db)} 条历史记录（文件可能已删除）"))
            existing_videos.update(db_videos)
    except Exception as e:
        logger.warning(f"查询数据库失败: {e}")

    # 收集所有视频数据
    total_downloaded = 0
    total_skipped = 0
    total_stats_saved = 0

    print(info("[下载] 正在获取视频列表..."))
    logger.info("正在获取视频列表...")

    try:
        async for aweme_data_list in handler.fetch_user_post_videos(
            sec_user_id, max_counts=max_counts or float("inf")
        ):
            video_list = aweme_data_list._to_list()

            if video_list:
                # 保存统计数据
                raw_data = aweme_data_list._to_raw()
                stats_saved = _save_video_metadata_from_raw(raw_data, nickname)
                total_stats_saved += stats_saved

                # 增量下载：过滤已存在的视频
                new_videos = []
                for video in video_list:
                    aweme_id = video.get('aweme_id', '') if isinstance(video, dict) else getattr(video, 'aweme_id', '')
                    if aweme_id and aweme_id not in existing_videos:
                        new_videos.append(video)
                        existing_videos.add(aweme_id)
                    else:
                        total_skipped += 1

                if new_videos:
                    # 只下载新视频
                    await handler.downloader.create_download_tasks(
                        kwargs, new_videos, user_path
                    )
                    total_downloaded += len(new_videos)
                    print(info(f"[下载] 本页 {len(new_videos)} 个新视频（跳过 {len(video_list) - len(new_videos)} 个已有）"))
                else:
                    print(info(f"[跳过] 本页 {len(video_list)} 个视频均为本地已有"))

                # 如果指定了 max_counts，检查是否已达到上限
                if max_counts and total_downloaded >= max_counts:
                    print(info(f"[限制] 已达到下载上限 ({max_counts} 个)"))
                    break

                print(info(f"[下载] 累计新增 {total_downloaded} 个，跳过 {total_skipped} 个已有"))
    except Exception as e:
        logger.error(f"下载过程中出错: {e}")
        print(error(f"下载过程中出错: {e}"))
        # 继续处理已下载的视频

    logger.info(f"保存了 {total_stats_saved} 条视频元数据")
    print(success(f"[统计] 新增 {total_downloaded} 个，跳过 {total_skipped} 个已有"))

    # 整理文件
    print(info("[整理] 重新组织文件..."))
    post_path = downloads_path / "douyin" / "post"
    folder_name = None
    
    # 处理 douyin/post 下的文件
    if post_path.exists():
        for folder in post_path.iterdir():
            if folder.is_dir():
                folder_name = _reorganize_files(folder.name, uid)
    
    # 处理直接在下载目录或子目录下的文件（兼容不同 F2 版本的下载路径）
    folder_name = _rename_videos_in_downloads(nickname, uid, downloads_path) or folder_name

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

    return {
        'success': True,
        'uid': uid,
        'nickname': nickname
    }


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

    # 【修复异步报错】：下载完成后触发自动转写（此时事件循环已关闭）
    if isinstance(result, dict) and result.get('success'):
        try:
            _trigger_auto_transcribe(result['uid'], result['nickname'])
        except Exception as e:
            print(f"⚠️ 自动转写失败: {e}")

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

    result = download_by_url(url, max_counts)

    # 检查是否开启全自动模式
    if isinstance(result, dict) and result.get('success'):
        _trigger_auto_transcribe(uid, name)
    
    return result


def _trigger_auto_transcribe(uid, nickname):
    """
    尝试触发自动转写
    如果配置开启了 auto_transcribe，则扫描博主目录下**最近下载**的视频并转写
    """
    import time
    
    config = get_config()
    if not config.is_auto_transcribe():
        return

    print("\n" + "="*60)
    print("⚡ [全自动模式] 视频已下载，正在准备自动转写...")
    print("="*60)

    try:
        # 查找博主文件夹
        downloads_path = config.get_download_path()
        user_dir = downloads_path / nickname
        
        # 如果昵称目录不存在，尝试用 UID
        if not user_dir.exists():
            user_dir = downloads_path / uid
        
        if not user_dir.exists():
            print("⚠️  未找到下载目录，跳过自动转写")
            return

        # 获取所有 mp4 视频
        all_mp4_files = list(user_dir.glob("*.mp4"))
        if not all_mp4_files:
            print("⚠️  未找到视频文件，跳过自动转写")
            return

        # 【优化】只转写最近 5 分钟内下载的文件
        # 避免每次下载都把历史记录重新转写一遍
        now = time.time()
        five_mins = 300  # 5分钟
        
        mp4_files = []
        for f in all_mp4_files:
            if (now - f.stat().st_mtime) < five_mins:
                mp4_files.append(f)

        if not mp4_files:
            print("⚠️  未发现最近下载的视频（均为旧文件），跳过转写")
            return

        print(f"🔍 扫描到 {len(all_mp4_files)} 个文件，其中 {len(mp4_files)} 个为新下载，开始排队转写...")
        
        # 调用 Pipeline 进行批量转写
        # 这里直接导入，使用批量接口支持并发（默认并发数为 6）
        from src.media_tools.pipeline.orchestrator import run_pipeline_batch

        results = run_pipeline_batch(mp4_files)

        # 统计与清理
        success_count = 0
        fail_count = 0
        deleted_count = 0

        for r in results:
            if r.success:
                success_count += 1
                # 【核心优化】如果开启配置且转写成功，删除原视频节省空间
                if config.is_auto_delete_video():
                    try:
                        if r.video_path.exists():
                            r.video_path.unlink()
                            deleted_count += 1
                    except Exception:
                        pass
            else:
                fail_count += 1

        # 打印结果汇总
        print("\n" + "="*60)
        print("🎉 自动转写完成!")
        
        delete_msg = f" | 🗑️ 已删除 {deleted_count} 个视频" if deleted_count > 0 else ""
        print(f"   总数: {len(results)} | ✅ 成功: {success_count} | ❌ 失败: {fail_count}{delete_msg}")
        print(f"   📂 文稿位置: ./transcripts/")
        if deleted_count > 0:
            print(f"   ✨ 已自动释放 {deleted_count * 50} MB+ 磁盘空间 (估算)")
        print("="*60 + "\n")

    except Exception as e:
        print(f"⚠️  自动转写过程出错: {e}")
        import traceback
        traceback.print_exc()


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
