"""
数据清理页面
"""

import streamlit as st
import time
from pathlib import Path

from web.constants import DOWNLOADS_DIR, DB_FILE, LOGS_DIR
from web.utils import format_size


def render_cleanup() -> None:
    """渲染数据清理页面"""
    st.title("🗑️ 数据清理")

    tab1, tab2, tab3 = st.tabs(["🎬 视频清理", "🗄️ 数据库清理", "📝 日志清理"])

    with tab1:
        _render_video_cleanup()
    with tab2:
        _render_db_cleanup()
    with tab3:
        _render_log_cleanup()


def _render_video_cleanup() -> None:
    """视频清理"""
    st.subheader("🎬 本地视频扫描")

    if DOWNLOADS_DIR.exists():
        video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
        total_size = sum(f.stat().st_size for f in video_files)

        st.info(f"共 {len(video_files)} 个视频文件，占用 {format_size(total_size)}")

        if st.button("清理已删除视频的数据库记录", type="primary"):
            with st.spinner("正在清理..."):
                ok = _clean_deleted_videos()
                if ok:
                    st.success("清理完成")
                else:
                    st.warning("无需清理")
    else:
        st.info("downloads 目录不存在")


def _render_db_cleanup() -> None:
    """数据库清理"""
    st.subheader("🗄️ 数据库管理")

    if DB_FILE.exists():
        db_size = DB_FILE.stat().st_size
        st.info(f"数据库文件大小: {format_size(db_size)}")

        # 显示数据库统计信息
        db_stats = _get_db_stats()
        if db_stats:
            st.info(f"数据库记录: {db_stats['video_count']} 条视频, {db_stats['user_count']} 个用户")

        if st.button("清理过期数据库记录", type="primary"):
            with st.spinner("正在清理..."):
                cleaned, skipped = _clean_db_records()
                if cleaned > 0:
                    st.success(f"清理完成: 已删除 {cleaned} 条记录，跳过 {skipped} 条")
                else:
                    st.info("无需清理，数据库记录与本地文件一致")
    else:
        st.info("数据库文件不存在")


def _render_log_cleanup() -> None:
    """日志清理"""
    st.subheader("📝 日志管理")

    if LOGS_DIR.exists():
        log_files = list(LOGS_DIR.glob("*.log"))
        total_size = sum(f.stat().st_size for f in log_files)

        st.info(f"共 {len(log_files)} 个日志文件，占用 {format_size(total_size)}")

        if st.button("清理 30 天前的旧日志", type="primary"):
            _clean_old_logs()
            st.success("清理完成")
    else:
        st.info("logs 目录不存在")


def _clean_deleted_videos() -> bool:
    """清理已删除视频的数据库记录"""
    try:
        from scripts.core.cleaner import clean_deleted_videos

        deleted, _ = clean_deleted_videos(auto_confirm=True)
        return deleted > 0
    except Exception:
        return False


def _get_db_stats() -> dict | None:
    """获取数据库统计信息"""
    try:
        from scripts.core.db_helper import execute_query

        video_count = execute_query("SELECT COUNT(*) FROM video_metadata")[0][0]
        user_count = execute_query("SELECT COUNT(*) FROM user_info_web")[0][0]
        return {"video_count": video_count, "user_count": user_count}
    except Exception:
        return None


def _clean_db_records() -> tuple[int, int]:
    """清理过期数据库记录，返回 (清理数量, 跳过数量)"""
    try:
        from scripts.core.cleaner import clean_deleted_videos

        cleaned, skipped = clean_deleted_videos(auto_confirm=True)
        return cleaned, skipped
    except Exception as e:
        st.error(f"清理失败: {e}")
        return 0, 0


def _clean_old_logs() -> None:
    """清理旧日志文件"""
    cutoff = time.time() - 30 * 24 * 3600  # 30 天前

    for f in LOGS_DIR.glob("*.log"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
