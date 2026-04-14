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

from .f2_helper import get_f2_kwargs as _build_f2_kwargs

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
from ..utils.logger import logger


def _get_skill_dir():
    """获取项目根目录"""
    return get_config().project_root


def _get_f2_kwargs() -> dict:
    """获取 F2 所需的配置参数"""
    return _build_f2_kwargs()


def _prepare_f2_temp_dir(downloads_path: Path) -> Path:
    """清理并重建 F2 临时目录，避免残留文件和缺失父目录。"""
    f2_temp_path = downloads_path / "douyin"
    if f2_temp_path.exists():
        if f2_temp_path.is_dir():
            shutil.rmtree(f2_temp_path)
        else:
            f2_temp_path.unlink()
        logger.info("已清理 F2 临时目录")
        logger.info(info("[清理] F2 临时目录"))
    f2_temp_path.mkdir(parents=True, exist_ok=True)
    return f2_temp_path


def _create_video_metadata_table():
    """确保视频元数据表存在"""
    config = get_config()
    db_path = config.get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA journal_mode=WAL;")
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
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
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


def _save_single_video_metadata(video: dict, nickname: str = "") -> int:
    """保存单个视频的元数据"""
    if not video:
        return 0

    aweme_id = video.get("aweme_id", "")
    if not aweme_id:
        return 0

    config = get_config()
    db_path = config.get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    stats = video.get("statistics", {}) or {}
    author = video.get("author", {}) or {}
    video_nickname = (
        video.get("nickname")
        or author.get("nickname")
        or nickname
    )
    uid = (
        video.get("uid")
        or author.get("uid")
        or video.get("sec_user_id", "")
    )

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
            uid,
            video_nickname,
            video.get("desc", ""),
            video.get("create_time", 0),
            video.get("video", {}).get("duration", 0) if video.get("video") else 0,
            stats.get("digg_count", 0),
            stats.get("comment_count", 0),
            stats.get("collect_count", 0),
            stats.get("share_count", 0),
            stats.get("play_count", 0),
            int(datetime.now().timestamp()),
        ),
    )

    conn.commit()
    conn.close()
    return 1


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
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        # 查询该博主所有视频标题（不限数量，确保批量下载时全部能匹配）
        cursor.execute(
            "SELECT aweme_id, desc FROM video_metadata WHERE uid = ? ORDER BY fetch_time DESC",
            (uid,)
        )
        recent_videos = cursor.fetchall()

        if not recent_videos:
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

            # 方法0：直接从文件名提取 aweme_id（处理 F2 原始格式如 7620767195682364133_video.mp4）
            aweme_id = None
            aweme_match = re.match(r'^(\d{15,})(?:_video)?$', stem)
            if aweme_match:
                candidate = aweme_match.group(1)
                if candidate in title_map:
                    aweme_id = candidate
                else:
                    # 不在 title_map 里，直接查 DB
                    cursor.execute("SELECT desc FROM video_metadata WHERE aweme_id = ?", (candidate,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        title_map[candidate] = row[0]
                        aweme_id = candidate

            # 方法1：尝试从文件名匹配 title_map 中的 aweme_id
            if not aweme_id:
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
                    logger.info(info(f"  [重命名] {f.name[:40]}... → {new_name[:40]}..."))
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
            logger.info(info(f"  [整理] 已处理 {processed_count} 个文件到 {folder_name}/（{renamed_count} 个已重命名）"))

            # 更新数据库中的 local_filename 字段
            cursor.execute(
                "UPDATE video_metadata SET local_filename = ? WHERE uid = ?",
                (folder_name, uid)
            )
            conn.commit()
            logger.info(info(f"  [更新] 已更新 {folder_name} 的 local_filename"))
    finally:
        if conn:
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
        logger.info(info(f"  [移动] {nickname} -> {folder_name} ({moved_count} 文件)"))

    return folder_name


def _sync_media_assets(uid: str, nickname: str, folder_name: str):
    """将 video_metadata 中的数据同步到全新的 V2 media_assets 表"""
    import re
    
    config = get_config()
    db_path = config.get_db_path()
    downloads_path = config.get_download_path()

    try:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        # 获取该用户的所有视频元数据
        cursor.execute("SELECT aweme_id, desc, duration FROM video_metadata WHERE uid = ?", (uid,))
        videos = cursor.fetchall()
        
        # 修复：优化文件查找算法，从O(N*M)降到O(N+M)
        # 先扫描一次所有文件，构建查找表
        user_dir = downloads_path / folder_name
        file_lookup = {}  # {aweme_id: filename}
        keyword_lookup = {}  # {keyword: filename}
        
        if user_dir.exists():
            # 一次性获取所有mp4文件
            all_files = list(user_dir.glob("*.mp4"))
            
            # 构建aweme_id查找表
            for f in all_files:
                # 尝试从文件名提取aweme_id（通常是19位数字）
                aweme_matches = re.findall(r'\d{19}', f.stem)
                for aweme_id in aweme_matches:
                    file_lookup[aweme_id] = f"{folder_name}/{f.name}"
                
                # 构建关键词查找表
                clean_stem = f.stem.lower()
                chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', clean_stem)
                for word in chinese_words:
                    if word not in keyword_lookup:
                        keyword_lookup[word] = f"{folder_name}/{f.name}"

        now = datetime.now().isoformat()

        for aweme_id, desc, duration in videos:
            # 尝试在查找表中寻找该视频文件
            video_path = ""
            video_status = "pending"
            
            # 方法1：通过aweme_id匹配
            if aweme_id in file_lookup:
                video_path = file_lookup[aweme_id]
                video_status = "downloaded"
            else:
                # 方法2：通过中文关键词匹配
                clean_title = _clean_video_title(desc)
                chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', clean_title)
                for word in chinese_words[:3]:  # 取前3个关键词
                    if word in keyword_lookup:
                        video_path = keyword_lookup[word]
                        video_status = "downloaded"
                        break

            # 插入或更新 media_assets 表
            cursor.execute("""
                INSERT OR IGNORE INTO media_assets
                (asset_id, creator_uid, title, duration, video_path, video_status, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                aweme_id, uid, desc, duration, video_path, video_status, now, now
            ))

            # 如果已经存在，则更新状态
            cursor.execute("""
                UPDATE media_assets
                SET video_path = ?, video_status = ?, update_time = ?
                WHERE asset_id = ? AND video_status != 'downloaded'
            """, (video_path, video_status, now, aweme_id))

        conn.commit()
    except Exception as e:
        logger.error(f"同步 media_assets 失败: {e}")
    finally:
        if conn:
            conn.close()

def _update_last_fetch_time(uid: str, nickname: str = ""):
    """更新 SQLite 中的 last_fetch_time"""
    try:
        config = get_config()
        db_path = config.get_db_path()
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE creators SET last_fetch_time = ? WHERE uid = ?",
                (datetime.now().isoformat(), uid)
            )
            conn.commit()
        logger.info(info(f"  [更新] last_fetch_time for {nickname or uid}"))
    except Exception as e:
        logger.error(f"更新 last_fetch_time 失败: {e}")





def _generate_data():
    """生成 Web 数据看板"""
    from .data_generator import generate_data

    generate_data()


async def _download_with_stats(url: str, max_counts: int = None, skip_existing: bool = True):
    """
    使用 F2 API 下载视频并保存统计数据

    Args:
        url: 用户主页 URL
        max_counts: 最大下载数量
    """
    from f2.apps.douyin.db import AsyncUserDB
    from f2.apps.douyin.handler import DouyinHandler

    logger.info(f"开始下载: {url}")
    kwargs = _get_f2_kwargs()
    kwargs["url"] = url

    if max_counts:
        kwargs["max_counts"] = max_counts
        logger.info(f"限制下载数量: {max_counts}")

    config = get_config()
    downloads_path = config.get_download_path()

    # 清理临时目录
    f2_temp_path = _prepare_f2_temp_dir(downloads_path)

    logger.info(info("[下载] 开始下载..."))
    logger.info(info(f"[路径] {downloads_path}"))
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
        logger.info(error("[错误] 无法解析用户 ID"))
        return False

    if not sec_user_id:
        logger.error("无法解析用户 ID")
        logger.info(error("[错误] 无法解析用户 ID"))
        return False

    logger.info(f"sec_user_id: {sec_user_id[:30]}...")
    logger.info(info(f"[信息] sec_user_id: {sec_user_id[:30]}..."))

    # 获取用户信息并保存
    async with AsyncUserDB(str(config.get_db_path())) as db:
        user_path = await handler.get_or_add_user_data(kwargs, sec_user_id, db)

    # 从数据库获取用户信息（通过 sec_user_id 查找）
    db_path = config.get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uid, nickname FROM user_info_web WHERE sec_user_id LIKE ? LIMIT 1",
        (f"{sec_user_id[:20]}%",)
    )
    user_info = cursor.fetchone()
    conn.close()
    
    # 如果没找到，使用最新记录（向后兼容）
    if not user_info:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
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
        logger.info(info(f"[博主] {nickname} (UID: {uid})"))

    # 统计本地已有视频（增量下载）
    existing_videos = set()
    if skip_existing:
        if user_path.exists():
            existing_videos = {f.stem for f in user_path.glob("*.mp4")}
            if existing_videos:
                logger.info(info(f"[本地] 已有 {len(existing_videos)} 个视频文件，将跳过已下载的"))

        # 同时从数据库获取已下载的视频 ID（防止文件被删除后重复下载）
        try:
            conn = sqlite3.connect(str(db_path), timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
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
                    logger.info(info(f"[数据库] 发现 {len(new_from_db)} 条历史记录（文件可能已删除）"))
                existing_videos.update(db_videos)
        except Exception as e:
            logger.warning(f"查询数据库失败: {e}")
    else:
        logger.info(info("[模式] 全量重拉：不跳过已存在视频"))

    # 收集所有视频数据
    total_downloaded = 0
    total_skipped = 0
    total_stats_saved = 0
    new_aweme_ids = []

    logger.info(info("[下载] 正在获取视频列表..."))
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

                # 增量/全量：过滤或全量重拉
                if skip_existing:
                    new_videos = []
                    for video in video_list:
                        aweme_id = video.get('aweme_id', '') if isinstance(video, dict) else getattr(video, 'aweme_id', '')
                        if aweme_id and aweme_id not in existing_videos:
                            new_videos.append(video)
                            existing_videos.add(aweme_id)
                        else:
                            total_skipped += 1
                else:
                    new_videos = list(video_list)

                if new_videos:
                    # 只下载新视频
                    await handler.downloader.create_download_tasks(
                        kwargs, new_videos, user_path
                    )
                    total_downloaded += len(new_videos)
                    for video in new_videos:
                        aweme_id = video.get('aweme_id', '') if isinstance(video, dict) else getattr(video, 'aweme_id', '')
                        if aweme_id:
                            new_aweme_ids.append(aweme_id)
                    if skip_existing:
                        logger.info(info(f"[下载] 本页 {len(new_videos)} 个新视频（跳过 {len(video_list) - len(new_videos)} 个已有）"))
                    else:
                        logger.info(info(f"[下载] 本页 {len(new_videos)} 个视频（全量重拉）"))
                else:
                    logger.info(info(f"[跳过] 本页 {len(video_list)} 个视频均为本地已有"))

                # 如果指定了 max_counts，检查是否已达到上限
                if max_counts and total_downloaded >= max_counts:
                    logger.info(info(f"[限制] 已达到下载上限 ({max_counts} 个)"))
                    break

                logger.info(info(f"[下载] 累计新增 {total_downloaded} 个，跳过 {total_skipped} 个已有"))
    except Exception as e:
        logger.error(f"下载过程中出错: {e}")
        logger.info(error(f"下载过程中出错: {e}"))
        # 继续处理已下载的视频

    logger.info(f"保存了 {total_stats_saved} 条视频元数据")
    logger.info(success(f"[统计] 新增 {total_downloaded} 个，跳过 {total_skipped} 个已有"))

    # 整理文件
    logger.info(info("[整理] 重新组织文件..."))
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

    # 同步 V2 资产库
    if folder_name:
        logger.info(info("[资产] 同步至媒体资产库..."))
        _sync_media_assets(uid, nickname, folder_name)

    # 生成 Web 数据文件
    logger.info(info("[数据] 生成 Web 数据文件..."))
    _generate_data()

    new_files = []
    if new_aweme_ids and folder_name:
        try:
            conn = sqlite3.connect(str(db_path), timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(new_aweme_ids))
            cursor.execute(f"SELECT video_path FROM media_assets WHERE asset_id IN ({placeholders})", new_aweme_ids)
            for row in cursor.fetchall():
                if row[0]:
                    full_path = downloads_path / row[0]
                    if full_path.exists():
                        new_files.append(str(full_path))
            conn.close()
        except Exception as e:
            logger.error(f"查询新文件路径失败: {e}")

    logger.info(f"下载完成: 共 {total_downloaded} 个视频")
    logger.info(success(f"\n[完成] 共下载 {total_downloaded} 个视频"))
    if folder_name:
        logger.info(info(f"[位置] {downloads_path / folder_name}"))

    return {
        'success': True,
        'uid': uid,
        'nickname': nickname,
        'new_files': new_files
    }


def download_by_url_sync(url, max_counts=None, skip_existing: bool = True):
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
            return asyncio.run(_download_with_stats(url, max_counts, skip_existing=skip_existing))
    except Exception as e:
        logger.info(error(f"下载出错: {e}"))
        return False


def download_by_url(url, max_counts=None, disable_auto_transcribe=False, skip_existing: bool = True):
    """
    通过 URL 下载单个博主的视频

    Args:
        url: 博主主页 URL
        max_counts: 最大下载数量
        disable_auto_transcribe: 是否禁用自动转写

    Returns:
        dict: 包含 success, uid, nickname, new_files 的字典，或 False
    """
    print_header("下载博主视频")
    logger.info(info(f"博主 URL: {url}"))
    if max_counts:
        logger.info(info(f"最大下载数量: {max_counts}"))
    logger.info()

    logger.info(info("开始下载..."))
    logger.info()

    result = download_by_url_sync(url, max_counts, skip_existing=skip_existing)

    # 【修复异步报错】：下载完成后触发自动转写（此时事件循环已关闭）
    if not disable_auto_transcribe and isinstance(result, dict) and result.get('success'):
        try:
            _trigger_auto_transcribe(result['uid'], result['nickname'])
        except Exception as e:
            logger.info(f"⚠️ 自动转写失败: {e}")

    if result:
        logger.info(success("下载完成！"))
        return result
    else:
        logger.info(error("下载失败，请检查日志"))
        return False


async def download_aweme_by_url(url: str):
    """按单个视频 URL 精确下载一个视频"""
    from f2.apps.douyin.db import AsyncUserDB
    from f2.apps.douyin.handler import DouyinHandler
    from f2.apps.douyin.utils import AwemeIdFetcher

    print_header("下载单个视频")
    logger.info(info(f"视频 URL: {url}"))
    logger.info()

    config = get_config()
    downloads_path = config.get_download_path()
    kwargs = _get_f2_kwargs()
    kwargs["url"] = url

    _prepare_f2_temp_dir(downloads_path)

    _create_video_metadata_table()

    try:
        aweme_id = await AwemeIdFetcher.get_aweme_id(url)
    except Exception as e:
        logger.info(error(f"解析视频 ID 失败: {e}"))
        return False

    if not aweme_id:
        logger.info(error("无法解析视频 ID"))
        return False

    handler = DouyinHandler(kwargs)

    try:
        aweme_data = await handler.fetch_one_video(aweme_id)
    except Exception as e:
        logger.info(error(f"获取视频详情失败: {e}"))
        return False

    aweme_dict = aweme_data._to_dict()
    uid = str(aweme_dict.get("uid") or aweme_dict.get("author", {}).get("uid") or "")
    nickname = str(aweme_dict.get("nickname") or aweme_dict.get("author", {}).get("nickname") or "")

    async with AsyncUserDB(str(config.get_db_path())) as db:
        user_path = await handler.get_or_add_user_data(kwargs, aweme_data.sec_user_id, db)

    before_files = {p.resolve() for p in user_path.glob("*.mp4")} if user_path.exists() else set()

    _save_single_video_metadata(aweme_dict, nickname=nickname)

    await handler.downloader.create_download_tasks(kwargs, aweme_dict, user_path)

    folder_name = None

    post_path = downloads_path / "douyin" / "post"
    if post_path.exists():
        for folder in post_path.iterdir():
            if folder.is_dir():
                folder_name = _reorganize_files(folder.name, uid) or folder_name

    folder_name = _rename_videos_in_downloads(nickname, uid, downloads_path) or folder_name or user_path.name

    if uid:
        _sync_media_assets(uid, nickname, folder_name)
        _update_last_fetch_time(uid, nickname or folder_name)

    _generate_data()

    new_files: list[str] = []
    target_dir = downloads_path / folder_name if folder_name else user_path
    if target_dir.exists():
        for file_path in target_dir.glob("*.mp4"):
            if file_path.resolve() not in before_files:
                new_files.append(str(file_path))

    try:
        with sqlite3.connect(str(config.get_db_path()), timeout=15.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT video_path FROM media_assets WHERE asset_id = ?",
                (aweme_id,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                full_path = downloads_path / row[0]
                if full_path.exists():
                    if str(full_path) not in new_files:
                        new_files.append(str(full_path))
    except Exception as e:
        logger.warning(f"查询单视频文件路径失败: {e}")

    logger.info(success(f"[完成] 单个视频下载成功: {aweme_id}"))
    return {
        "success": True,
        "uid": uid,
        "nickname": nickname,
        "aweme_id": aweme_id,
        "new_files": new_files,
    }


def download_by_uid(uid, max_counts=None, skip_existing: bool = True):
    """
    通过 UID 下载博主视频

    Args:
        uid: 用户 UID
        max_counts: 最大下载数量

    Returns:
        是否成功
    """
    from .following_mgr import get_user

    user = get_user(uid)
    if not user:
        logger.info(error(f"用户 {uid} 不在关注列表中"))
        return False

    # 构建 URL
    sec_user_id = user.get("sec_user_id", "")
    if sec_user_id and sec_user_id.startswith("MS4w"):
        url = f"https://www.douyin.com/user/{sec_user_id}"
    else:
        url = f"https://www.douyin.com/user/{uid}"

    name = user.get("nickname", user.get("name", "未知"))
    logger.info(info(f"博主: {name} (UID: {uid})"))

    result = download_by_url(url, max_counts, skip_existing=skip_existing)
    
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

    logger.info("\n" + "="*60)
    logger.info("⚡ [全自动模式] 视频已下载，正在准备自动转写...")
    logger.info("="*60)

    try:
        # 查找博主文件夹
        downloads_path = config.get_download_path()
        user_dir = downloads_path / nickname
        
        # 如果昵称目录不存在，尝试用 UID
        if not user_dir.exists():
            user_dir = downloads_path / uid
        
        if not user_dir.exists():
            logger.info("⚠️  未找到下载目录，跳过自动转写")
            return

        # 获取所有 mp4 视频
        all_mp4_files = list(user_dir.glob("*.mp4"))
        if not all_mp4_files:
            logger.info("⚠️  未找到视频文件，跳过自动转写")
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
            logger.info("⚠️  未发现最近下载的视频（均为旧文件），跳过转写")
            return

        logger.info(f"🔍 扫描到 {len(all_mp4_files)} 个文件，其中 {len(mp4_files)} 个为新下载，开始排队转写...")
        
        # 调用 Pipeline 进行批量转写
        # 这里直接导入，使用批量接口支持并发（默认并发数为 6）
        from media_tools.pipeline.orchestrator import run_pipeline_batch

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
        logger.info("\n" + "="*60)
        logger.info("🎉 自动转写完成!")
        
        delete_msg = f" | 🗑️ 已删除 {deleted_count} 个视频" if deleted_count > 0 else ""
        logger.info(f"   总数: {len(results)} | ✅ 成功: {success_count} | ❌ 失败: {fail_count}{delete_msg}")
        logger.info(f"   📂 文稿位置: ./transcripts/")
        if deleted_count > 0:
            logger.info(f"   ✨ 已自动释放 {deleted_count * 50} MB+ 磁盘空间 (估算)")
        logger.info("="*60 + "\n")

    except Exception as e:
        logger.info(f"⚠️  自动转写过程出错: {e}")
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
        logger.info(info("关注列表为空"))
        logger.info(info("请先使用 '添加博主' 功能添加关注"))
        return 0, 0

    logger.info(info(f"共 {len(users)} 位博主"))
    logger.info()

    if not auto_confirm:
        confirm = input("确认开始下载？(y/N): ").strip().lower()
        if confirm != "y":
            logger.info(info("已取消"))
            return 0, 0

    success_count = 0
    failed_count = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        name = user.get("nickname", user.get("name", "未知"))

        logger.info()
        logger.info(info(f"[{i}/{len(users)}] 下载: {name}"))

        ok = download_by_uid(uid)
        if ok:
            success_count += 1
        else:
            failed_count += 1

    logger.info()
    print_header("下载完成")
    logger.info(success(f"成功: {success_count}"))
    logger.info(error(f"失败: {failed_count}"))

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
        logger.info(info("关注列表为空"))
        logger.info(info("请先使用 '添加博主' 功能添加关注"))
        return 0, 0

    config = get_config()
    downloads_path = config.get_download_path()

    # 显示用户列表
    logger.info(info("选择要下载的博主（输入序号，逗号分隔，all=全部，q=返回）"))
    logger.info()

    for i, user in enumerate(users, 1):
        uid = user.get("uid", "未知")
        name = user.get("nickname", user.get("name", "未知"))
        folder = user.get("folder", name or uid)
        user_dir = downloads_path / folder
        local_count = len(list(user_dir.glob("*.mp4"))) if user_dir.exists() else 0

        status = f"已下载 {local_count} 个" if local_count > 0 else "未下载"
        logger.info(f"  {i:2}. {name} ({status})")

    logger.info()
    choice = input("请选择: ").strip().lower()

    if choice == "q" or not choice:
        logger.info(info("已取消"))
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
                logger.info(warning(f"无效的序号: {idx}"))

        if not selected:
            logger.info(error("没有有效的选择"))
            return 0, 0

        logger.info()
        logger.info(info(f"已选择 {len(selected)} 个博主"))

        success_count = 0
        failed_count = 0

        for i, user in enumerate(selected, 1):
            uid = user.get("uid")
            name = user.get("nickname", user.get("name", "未知"))

            logger.info()
            logger.info(info(f"[{i}/{len(selected)}] 下载: {name}"))

            ok = download_by_uid(uid)
            if ok:
                success_count += 1
            else:
                failed_count += 1

        logger.info()
        logger.info(success(f"下载完成: 成功 {success_count}，失败 {failed_count}"))
        return success_count, failed_count

    except ValueError:
        logger.info(error("无效的输入，请输入数字"))
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
        logger.info(info("关注列表为空"))
        return 0, 0

    logger.info(info(f"每个博主只下载 1 个视频"))
    logger.info(info(f"共 {len(users)} 位博主"))
    logger.info()

    if not auto_confirm:
        confirm = input("确认开始？(y/N): ").strip().lower()
        if confirm != "y":
            logger.info(info("已取消"))
            return 0, 0

    success_count = 0
    failed_count = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        name = user.get("nickname", user.get("name", "未知"))

        logger.info(info(f"[{i}/{len(users)}] 采样: {name}"))

        ok = download_by_uid(uid, max_counts=1)
        if ok:
            success_count += 1
        else:
            failed_count += 1

    logger.info()
    logger.info(success(f"采样完成: 成功 {success_count}，失败 {failed_count}"))
    return success_count, failed_count
