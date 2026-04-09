#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据生成脚本 - 扫描下载目录和 following.json，生成前端可用数据
包含视频元数据（点赞、评论、收藏、分享数）
"""
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

# 强制使用脚本所在目录作为工作目录
SKILL_DIR = Path(__file__).parent.parent.resolve()
os.chdir(SKILL_DIR)

# 导入统一配置模块
from utils.logger import logger
from utils.config import get_db_path, get_download_path, get_following_path
from utils.following import load_following

# 技能目录
SKILL_DIR = Path(__file__).parent.parent.resolve()

DOWNLOADS_PATH = get_download_path()
FOLLOWING_PATH = get_following_path()
DB_PATH = get_db_path()
OUTPUT_PATH = DOWNLOADS_PATH / "data.js"

# index.html 模板位置
INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>抖音视频数据面板</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #3b82f6;
            --accent-hover: #60a5fa;
            --border: rgba(255, 255, 255, 0.1);
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 0;
            background: linear-gradient(180deg, rgba(59,130,246,0.1) 0%, transparent 100%);
            border-radius: 16px;
            position: relative;
        }

        h1 {
            margin: 0 0 10px 0;
            font-size: 2.5em;
            background: linear-gradient(to right, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stats-summary {
            display: flex;
            justify-content: center;
            gap: 30px;
            color: var(--text-muted);
            flex-wrap: wrap;
        }

        .filter-bar {
            margin-top: 20px;
            display: flex;
            justify-content: center;
            gap: 15px;
        }

        .filter-bar select, .filter-bar input {
            padding: 8px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: rgba(0,0,0,0.3);
            color: var(--text-main);
            outline: none;
        }

        .author-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .author-card:hover {
            transform: translateY(-2px);
            border-color: var(--accent);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        .author-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .author-info h2 {
            margin: 0 0 8px 0;
            color: var(--accent-hover);
        }

        .author-stats {
            display: flex;
            gap: 20px;
            color: var(--text-muted);
            font-size: 0.9em;
        }

        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 24px;
            display: none; /* 默认折叠 */
        }

        .author-card.active .video-grid {
            display: flex;
            flex-wrap: wrap;
            animation: fadeIn 0.4s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .video-card {
            background: rgba(0,0,0,0.2);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.2s;
            width: 100%;
            max-width: 280px;
            flex: 1 1 280px;
            cursor: default;
        }

        .video-card:hover {
            transform: scale(1.02);
            border-color: var(--text-muted);
        }

        .video-cover {
            width: 100%;
            height: 160px;
            background: #000;
            position: relative;
        }

        .video-cover video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            cursor: pointer;
        }

        .video-info {
            padding: 16px;
        }

        .video-title {
            font-size: 0.9em;
            margin: 0 0 12px 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            color: #e2e8f0;
        }

        .video-stats {
            display: flex;
            justify-content: space-between;
            font-size: 0.8em;
            color: var(--text-muted);
        }

        .stat-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px dashed var(--border);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>抖音视频数据面板</h1>
            <div class="stats-summary" id="globalStats">
                <!-- 动态填充 -->
            </div>

            <div class="filter-bar">
                <input type="text" id="searchInput" placeholder="搜索视频标题..." onkeyup="handleSearch(event)">
                <select id="sortSelect" onchange="renderAuthors()">
                    <option value="digg_desc">❤️ 点赞量 (从高到低)</option>
                    <option value="time_desc">⏱️ 最新发布</option>
                    <option value="time_asc">⏱️ 最早发布</option>
                    <option value="comment_desc">💬 评论量 (从高到低)</option>
                    <option value="size_desc">💾 文件大小 (从大到小)</option>
                </select>
                <button onclick="renderAuthors()" style="background: var(--accent); color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer;">应用</button>
            </div>
        </header>

        <div id="authorsList">
            <!-- 动态填充 -->
        </div>
    </div>

    <!-- 引入生成的静态数据 -->
    <script src="data.js"></script>
    <script>
        function formatNumber(num) {
            if (num >= 100000000) return (num / 100000000).toFixed(1) + '亿';
            if (num >= 10000) return (num / 10000).toFixed(1) + '万';
            return num.toString();
        }

        function formatSize(bytes) {
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
            return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB';
        }

        let searchQuery = "";
        let currentSort = "digg_desc";

        function handleSearch(e) {
            searchQuery = e.target.value.toLowerCase();
            if (e.key === 'Enter') {
                renderAuthors();
            }
        }

        function sortVideos(videos, sortType) {
            return [...videos].sort((a, b) => {
                switch (sortType) {
                    case 'digg_desc':
                        return (b.stats?.digg_count || 0) - (a.stats?.digg_count || 0);
                    case 'time_desc':
                        return (b.stats?.create_time || 0) - (a.stats?.create_time || 0);
                    case 'time_asc':
                        return (a.stats?.create_time || 0) - (b.stats?.create_time || 0);
                    case 'comment_desc':
                        return (b.stats?.comment_count || 0) - (a.stats?.comment_count || 0);
                    case 'size_desc':
                        return (b.size || 0) - (a.size || 0);
                    default:
                        return 0;
                }
            });
        }

        function renderAuthors() {
            const data = window.APP_DATA;
            const sortSelect = document.getElementById('sortSelect');
            currentSort = sortSelect ? sortSelect.value : 'digg_desc';

            // 渲染博主列表
            const authorsHtml = data.users.map(user => {
                // 筛选该博主的视频并搜索过滤
                let userVideos = data.videos.filter(v => v.folder === user.folder);

                if (searchQuery) {
                    userVideos = userVideos.filter(v => {
                        const title = v.stats?.desc || v.name;
                        return title.toLowerCase().includes(searchQuery);
                    });
                }

                if (userVideos.length === 0 && searchQuery) return ''; // 搜索时隐藏没有结果的博主

                // 排序
                userVideos = sortVideos(userVideos, currentSort);

                const videosHtml = userVideos.map(v => `
                    <div class="video-card" onclick="event.stopPropagation()">
                        <div class="video-cover">
                            <video src="./${encodeURIComponent(user.folder)}/${encodeURIComponent(v.name)}.mp4" controls preload="none" poster="./${encodeURIComponent(user.folder)}/${encodeURIComponent(v.name)}.jpg"></video>
                        </div>
                        <div class="video-info">
                            <h3 class="video-title" title="${v.stats?.desc || v.name}">${v.stats?.desc || v.name}</h3>
                            <div class="video-stats">
                                <span class="stat-item">❤️ ${formatNumber(v.stats?.digg_count || 0)}</span>
                                <span class="stat-item">💬 ${formatNumber(v.stats?.comment_count || 0)}</span>
                                <span class="stat-item">💾 ${formatSize(v.size)}</span>
                            </div>
                        </div>
                    </div>
                `).join('');

                // 默认搜索时展开有结果的折叠面板
                const activeClass = searchQuery ? 'active' : '';

                return `
                    <div class="author-card ${activeClass}" onclick="this.classList.toggle('active')">
                        <div class="author-header">
                            <div class="author-info">
                                <h2>${user.name || user.uid}</h2>
                                <div class="author-stats">
                                    <span>本地视频: ${user.video_count} ${searchQuery ? `(匹配 ${userVideos.length} 个)` : ''}</span>
                                    <span>获赞总数: ${formatNumber(user.stats?.total_diggs || 0)}</span>
                                </div>
                            </div>
                            <div style="color: var(--text-muted); font-size: 0.9em;">
                                点击展开/折叠 ▼
                            </div>
                        </div>
                        <div class="video-grid">
                            ${videosHtml}
                        </div>
                    </div>
                `;
            }).join('');

            const authorsList = document.getElementById('authorsList');
            if (authorsHtml) {
                authorsList.innerHTML = authorsHtml;
            } else {
                authorsList.innerHTML = `<div class="empty-state">没有找到匹配的视频</div>`;
            }
        }

        function render() {
            if (!window.APP_DATA) {
                document.getElementById('authorsList').innerHTML = '<div class="empty-state">暂无数据，请先运行 python scripts/generate-data.py</div>';
                return;
            }

            const data = window.APP_DATA;

            // 渲染全局统计
            const totalDiggs = data.videos.reduce((sum, v) => sum + (v.stats?.digg_count || 0), 0);
            const totalSize = data.videos.reduce((sum, v) => sum + (v.size || 0), 0);

            document.getElementById('globalStats').innerHTML = `
                <span>👤 收录博主: ${data.users.length}</span>
                <span>🎬 本地视频: ${data.videos.length}</span>
                <span>❤️ 累计点赞: ${formatNumber(totalDiggs)}</span>
                <span>💾 占用空间: ${formatSize(totalSize)}</span>
                <span>⏱️ 更新于: ${new Date(data.generated_at).toLocaleString()}</span>
            `;

            renderAuthors();
        }

        // 初始化渲染
        render();
    </script>
</body>
</html>
"""


def copy_index_template():
    """写入 index.html 模板到下载目录"""
    dest = DOWNLOADS_PATH / "index.html"
    with open(dest, "w", encoding="utf-8") as f:
        f.write(INDEX_TEMPLATE)
    return True


def extract_aweme_id(filename: str) -> str:
    """从文件名提取 aweme_id

    文件名格式: {时间戳}_{描述}_{aweme_id}_video.mp4
    例如: 2023-09-11 20-55-58_描述_7277551294787620150_video.mp4

    注意：描述中可能包含下划线，所以需要找所有纯数字段，然后选择合适的
    aweme_id 通常是 18-19 位数字，以 7 开头
    """
    stem = Path(filename).stem

    # 移除末尾的 _video
    stem = re.sub(r"_video$", "", stem)

    # 找所有纯数字段
    parts = stem.split("_")
    numeric_parts = []

    for part in parts:
        part = part.strip()
        # 检查是否是纯数字且长度 >= 15 (aweme_id 通常是 18-19 位)
        if part.isdigit() and len(part) >= 15:
            numeric_parts.append(part)

    # 如果找到纯数字段，返回最长的那个（应该是 aweme_id）
    if numeric_parts:
        return max(numeric_parts, key=len)

    # 回退方案：使用正则表达式找最长的数字串（15位以上）
    matches = re.findall(r"\d{15,}", stem)
    if matches:
        return max(matches, key=len)

    return stem  # 最后返回文件名


def format_size(bytes_size):
    """格式化文件大小"""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    if bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    if bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / 1024 / 1024:.1f} MB"
    return f"{bytes_size / 1024 / 1024 / 1024:.2f} GB"


def format_number(num):
    """格式化数字（大数用万/亿表示）"""
    if num >= 100000000:  # 1亿
        return f"{num / 100000000:.1f}亿"
    if num >= 10000:  # 1万
        return f"{num / 10000:.1f}万"
    return str(num)


def get_video_metadata():
    """从数据库获取视频元数据"""
    if not DB_PATH.exists():
        return {}

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # 检查 video_metadata 表是否存在
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='video_metadata'
        """
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

        # 以 aweme_id 为键建立索引
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


def scan_videos_from_root(metadata: dict):
    """扫描下载目录下所有子目录中的视频文件"""
    videos = []
    # 扫描所有子目录中的 mp4 文件
    for video_file in sorted(DOWNLOADS_PATH.rglob("*.mp4")):
        stat = video_file.stat()
        # 获取视频文件的直接父目录名作为 folder (即博主昵称)
        parent_dir = video_file.parent.name

        # 提取 aweme_id
        aweme_id = extract_aweme_id(video_file.name)

        video_data = {
            "name": video_file.stem,
            "aweme_id": aweme_id,
            "size": stat.st_size,
            "folder": parent_dir,
        }

        # 合并元数据
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


def scan_user_videos(user_folder: str, metadata: dict):
    """扫描指定用户目录的视频文件"""
    user_dir = DOWNLOADS_PATH / user_folder

    if not user_dir.exists():
        return []

    videos = []
    for video_file in sorted(user_dir.glob("*.mp4")):
        stat = video_file.stat()
        aweme_id = video_file.stem.split("_")[0]

        video_data = {
            "name": video_file.stem,
            "aweme_id": aweme_id,
            "size": stat.st_size,
            "folder": user_folder,
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


def calculate_user_stats(videos: list) -> dict:
    """计算用户统计信息"""
    total_diggs = sum(v.get("stats", {}).get("digg_count", 0) for v in videos)
    total_comments = sum(v.get("stats", {}).get("comment_count", 0) for v in videos)
    total_collects = sum(v.get("stats", {}).get("collect_count", 0) for v in videos)
    total_shares = sum(v.get("stats", {}).get("share_count", 0) for v in videos)

    # 找出热门视频（点赞最多的前3个）
    sorted_videos = sorted(
        videos, key=lambda x: x.get("stats", {}).get("digg_count", 0), reverse=True
    )
    top_videos = sorted_videos[:3]

    return {
        "total_diggs": total_diggs,
        "total_comments": total_comments,
        "total_collects": total_collects,
        "total_shares": total_shares,
        "top_videos": [
            {"name": v["name"], "digg_count": v.get("stats", {}).get("digg_count", 0)}
            for v in top_videos
        ],
    }


def main():
    logger.info("开始生成数据文件...")

    # 1. 读取 following.json
    following = load_following()
    if not following.get("users"):
        logger.info("警告: 关注列表为空")

    # 2. 获取视频元数据
    metadata = get_video_metadata()
    logger.info(f"从数据库读取 {len(metadata)} 条视频元数据")

    # 3. 初始化数据结构
    data = {
        "generated_at": datetime.now().isoformat(),
        "download_path": str(DOWNLOADS_PATH),
        "users": [],
        "videos": [],
    }

    # 4. 先扫描根目录下的所有视频
    all_videos = scan_videos_from_root(metadata)

    # 5. 构建用户数据
    # 支持两种 following.json 格式：
    #   - 旧格式：单个用户对象，uid 作为键
    #   - 新格式：users 数组

    if following.get("users") and isinstance(following["users"], list):
        # 新格式：users 是数组
        for user in following["users"]:
            uid = user.get("uid")
            nickname = user.get("nickname", user.get("name", ""))
            folder = user.get("folder", nickname or uid)  # 使用 folder 字段或 nickname

            if not uid:
                continue

            # 从根目录扫描结果中筛选该用户的视频（按 folder 匹配）
            user_videos = [v for v in all_videos if v["folder"] == folder]
            user_stats = calculate_user_stats(user_videos)

            data["users"].append(
                {
                    "uid": uid,
                    "name": nickname,
                    "folder": folder,
                    "avatar_url": user.get("avatar_url", ""),
                    "video_count": len(user_videos),
                    "stats": user_stats,
                }
            )
    else:
        # 旧格式：单个用户对象，uid 作为键
        for uid, user_info in following.items():
            # 跳过非用户字段（如"说明"）
            if isinstance(user_info, dict) and user_info.get("uid"):
                nickname = user_info.get("nickname", user_info.get("name", ""))
                folder = user_info.get("folder", nickname or uid)

                # 从根目录扫描结果中筛选该用户的视频（按 folder 匹配）
                user_videos = [v for v in all_videos if v["folder"] == folder]

                # 同时从用户目录扫描（如果存在）
                subdir_videos = scan_user_videos(folder, metadata)
                user_videos.extend(subdir_videos)

                user_stats = calculate_user_stats(user_videos)

                data["users"].append(
                    {
                        "uid": uid,
                        "name": nickname,
                        "folder": folder,
                        "avatar_url": user_info.get("avatar_url", ""),
                        "video_count": len(user_videos),
                        "stats": user_stats,
                    }
                )

    data["videos"] = all_videos

    # 6. 计算总大小和总统计
    total_size = sum(v["size"] for v in data["videos"])
    videos_with_stats = sum(1 for v in data["videos"] if "stats" in v)
    total_diggs = sum(v.get("stats", {}).get("digg_count", 0) for v in data["videos"])

    # 7. 写入 data.js
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("// 自动生成 - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        f.write(
            f"// 视频总数: {len(data['videos'])}, 有统计: {videos_with_stats}, 总点赞: {format_number(total_diggs)}\n"
        )
        f.write("window.APP_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    # 8. 复制 index.html 模板
    copied = copy_index_template()

    logger.info(f"✅ 数据已生成: {OUTPUT_PATH}")
    logger.info(f"   下载目录: {DOWNLOADS_PATH}")
    logger.info(f"   博主: {len(data['users'])}")
    logger.info(f"   视频: {len(data['videos'])}")
    logger.info(f"   有统计数据的视频: {videos_with_stats}")
    logger.info(f"   总大小: {format_size(total_size)}")
    logger.info(f"   总点赞: {format_number(total_diggs)}")
    logger.info("\n提示: 直接用浏览器打开 index.html 即可")
    logger.info(f"       {DOWNLOADS_PATH / 'index.html'}")


if __name__ == "__main__":
    main()
