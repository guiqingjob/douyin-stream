"""
统计面板组件
"""

import logging
import streamlit as st

from web.constants import DOWNLOADS_DIR, TRANSCRIPTS_DIR
from web.utils import format_size


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


@st.cache_data(ttl=60)  # 60秒缓存
def _get_stats() -> dict:
    """获取统计数据（带 60 秒缓存）
    
    Returns:
        dict: 包含 following_count, downloaded_videos, transcripts_count, disk_usage
    """
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
    except Exception as e:
        logging.warning(f"获取关注列表失败: {e}")

    # 已下载视频数
    if DOWNLOADS_DIR.exists():
        try:
            video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
            stats["downloaded_videos"] = len(video_files)
        except Exception as e:
            logging.warning(f"扫描下载目录失败: {e}")

    # 已转写文稿数
    if TRANSCRIPTS_DIR.exists():
        try:
            md_files = list(TRANSCRIPTS_DIR.rglob("*.md"))
            stats["transcripts_count"] = len(md_files)
        except Exception as e:
            logging.warning(f"扫描转写目录失败: {e}")

    # 磁盘占用
    total_size = 0
    for d in [DOWNLOADS_DIR, TRANSCRIPTS_DIR]:
        if d.exists():
            try:
                total_size += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            except Exception as e:
                logging.warning(f"计算目录大小失败: {e}")

    stats["disk_usage"] = format_size(total_size)

    return stats
