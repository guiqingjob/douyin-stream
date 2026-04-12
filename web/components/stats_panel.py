"""
统计面板组件
"""

import streamlit as st
from pathlib import Path


def render_stats_panel() -> None:
    """渲染统计面板"""
    st.subheader("📊 使用统计")

    stats = _get_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("关注博主数", stats.get("following_count", 0))
    with col2:
        st.metric("已下载视频", stats.get("downloaded_videos", 0))
    with col3:
        st.metric("已转写文稿", stats.get("transcripts_count", 0))
    with col4:
        st.metric("磁盘占用", stats.get("disk_usage", "0 MB"))


def _get_stats() -> dict:
    """获取统计数据"""
    stats = {
        "following_count": 0,
        "downloaded_videos": 0,
        "transcripts_count": 0,
        "disk_usage": "0 MB",
    }

    # 关注数
    try:
        from media_tools.douyin.utils.following import list_users

        users = list_users()
        stats["following_count"] = len(users)
    except Exception:
        pass

    # 已下载视频数
    downloads_dir = Path("downloads")
    if downloads_dir.exists():
        video_files = list(downloads_dir.rglob("*.mp4"))
        stats["downloaded_videos"] = len(video_files)

    # 已转写文稿数
    transcripts_dir = Path("transcripts")
    if transcripts_dir.exists():
        md_files = list(transcripts_dir.rglob("*.md"))
        stats["transcripts_count"] = len(md_files)

    # 磁盘占用
    total_size = 0
    for d in [downloads_dir, transcripts_dir]:
        if d.exists():
            total_size += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())

    if total_size > 1024 * 1024 * 1024:
        stats["disk_usage"] = f"{total_size / (1024**3):.2f} GB"
    elif total_size > 1024 * 1024:
        stats["disk_usage"] = f"{total_size / (1024**2):.2f} MB"
    else:
        stats["disk_usage"] = f"{total_size / 1024:.2f} KB"

    return stats
