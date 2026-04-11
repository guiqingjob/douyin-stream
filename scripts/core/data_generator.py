#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据看板生成模块
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from .ui import (
    format_number,
    format_size,
    info,
    print_header,
    print_status,
    success,
)
from .config_mgr import get_config
from .following_mgr import list_users


def generate_data():
    """
    生成 Web 数据看板

    Returns:
        是否成功
    """
    print_header("生成数据看板")

    config = get_config()
    downloads_path = config.get_download_path()
    db_path = config.get_db_path()

    # 1. 读取关注列表
    users = list_users()
    if not users:
        print(info("关注列表为空"))

    # 2. 获取视频元数据
    metadata = _get_video_metadata(db_path)
    print(info(f"从数据库读取 {len(metadata)} 条视频元数据"))

    # 3. 扫描视频文件
    all_videos = _scan_videos(downloads_path, metadata)
    print(info(f"扫描到 {len(all_videos)} 个视频文件"))

    # 4. 构建用户数据
    user_data = _build_user_data(users, all_videos, downloads_path)

    # 5. 组装数据
    data = {
        "generated_at": datetime.now().isoformat(),
        "download_path": str(downloads_path),
        "users": user_data,
        "videos": all_videos,
    }

    # 6. 写入 data.js
    output_path = downloads_path / "data.js"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"// 自动生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(
            f"// 视频总数: {len(data['videos'])}, 总点赞: {format_number(sum(v.get('stats', {}).get('digg_count', 0) for v in data['videos']))}\n"
        )
        f.write("window.APP_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    print(success(f"数据已生成: {output_path}"))

    # 7. 复制 index.html 模板
    _copy_index_template(downloads_path)

    # 8. 显示统计
    total_videos = len(all_videos)
    total_users = len(user_data)
    total_size = sum(v.get("size", 0) for v in all_videos)
    total_diggs = sum(
        v.get("stats", {}).get("digg_count", 0) for v in all_videos
    )

    print()
    print(info(f"收录博主: {total_users}"))
    print(info(f"本地视频: {total_videos}"))
    print(info(f"累计点赞: {format_number(total_diggs)}"))
    print(info(f"占用空间: {format_size(total_size)}"))
    print()
    print(success(f"直接用浏览器打开: {downloads_path / 'index.html'}"))

    return True


def _get_video_metadata(db_path):
    """从数据库获取视频元数据"""
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='video_metadata'"
        )
        if not cursor.fetchone():
            conn.close()
            return {}

        cursor.execute(
            """
            SELECT
                aweme_id, uid, nickname, desc, create_time, duration,
                digg_count, comment_count, collect_count, share_count, play_count,
                local_filename, file_size, fetch_time
            FROM video_metadata
        """
        )
        rows = cursor.fetchall()
        conn.close()

        metadata = {}
        for row in rows:
            aweme_id = row[0]
            metadata[aweme_id] = {
                "uid": row[1] or "",
                "nickname": row[2] or "",
                "desc": row[3] or "",
                "create_time": row[4] or 0,
                "duration": row[5] or 0,
                "digg_count": row[6] or 0,
                "comment_count": row[7] or 0,
                "collect_count": row[8] or 0,
                "share_count": row[9] or 0,
                "play_count": row[10] or 0,
                "local_filename": row[11] or "",
                "file_size": row[12] or 0,
                "fetch_time": row[13] or 0,
            }
        return metadata
    except sqlite3.OperationalError:
        conn.close()
        return {}


def _extract_aweme_id(filename):
    """从文件名提取 aweme_id"""
    stem = Path(filename).stem
    stem = re.sub(r"_video$", "", stem)

    parts = stem.split("_")
    numeric_parts = [p for p in parts if p.isdigit() and len(p) >= 15]

    if numeric_parts:
        return max(numeric_parts, key=len)

    matches = re.findall(r"\d{15,}", stem)
    if matches:
        return max(matches, key=len)

    return stem


def _scan_videos(downloads_path, metadata):
    """扫描下载目录下所有视频文件"""
    videos = []

    for video_file in sorted(downloads_path.rglob("*.mp4")):
        stat = video_file.stat()
        parent_dir = video_file.parent.name
        aweme_id = _extract_aweme_id(video_file.name)

        video_data = {
            "name": video_file.stem,
            "aweme_id": aweme_id,
            "size": stat.st_size,
            "folder": parent_dir,
        }

        if aweme_id in metadata:
            meta = metadata[aweme_id]
            video_data["stats"] = {
                "digg_count": meta["digg_count"],
                "comment_count": meta["comment_count"],
                "collect_count": meta["collect_count"],
                "share_count": meta["share_count"],
                "play_count": meta["play_count"],
            }
            video_data["desc"] = meta["desc"]
            video_data["create_time"] = meta["create_time"]
            video_data["duration"] = meta["duration"]
            if meta["nickname"]:
                video_data["nickname"] = meta["nickname"]

        videos.append(video_data)

    return videos


def _build_user_data(users, all_videos, downloads_path):
    """构建用户数据"""
    user_data = []

    for user in users:
        uid = user.get("uid")
        nickname = user.get("nickname", user.get("name", ""))
        folder = user.get("folder", nickname or uid)

        if not uid:
            continue

        # 筛选该用户的视频
        user_videos = [v for v in all_videos if v["folder"] == folder]

        # 计算统计信息
        total_diggs = sum(v.get("stats", {}).get("digg_count", 0) for v in user_videos)
        total_comments = sum(
            v.get("stats", {}).get("comment_count", 0) for v in user_videos
        )
        total_collects = sum(
            v.get("stats", {}).get("collect_count", 0) for v in user_videos
        )
        total_shares = sum(
            v.get("stats", {}).get("share_count", 0) for v in user_videos
        )

        user_data.append(
            {
                "uid": uid,
                "name": nickname,
                "folder": folder,
                "avatar_url": user.get("avatar_url", ""),
                "video_count": len(user_videos),
                "stats": {
                    "total_diggs": total_diggs,
                    "total_comments": total_comments,
                    "total_collects": total_collects,
                    "total_shares": total_shares,
                },
            }
        )

    return user_data


def _copy_index_template(downloads_path):
    """复制 index.html 模板"""
    dest = downloads_path / "index.html"

    # 简单模板，实际使用可从 templates/ 加载
    template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>抖音视频数据面板</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; }
        h1 { text-align: center; }
        #loading { text-align: center; padding: 40px; }
    </style>
</head>
<body>
    <h1>抖音视频数据面板</h1>
    <div id="loading">数据加载中...</div>
    <script src="data.js"></script>
    <script>
        if (window.APP_DATA) {
            document.getElementById('loading').innerHTML =
                '<p>博主: ' + APP_DATA.users.length + '</p>' +
                '<p>视频: ' + APP_DATA.videos.length + '</p>' +
                '<p>生成于: ' + APP_DATA.generated_at + '</p>';
        }
    </script>
</body>
</html>
"""

    with open(dest, "w", encoding="utf-8") as f:
        f.write(template)

    return True
