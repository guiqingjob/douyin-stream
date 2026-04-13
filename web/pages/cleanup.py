"""
清理与备份页面
"""

import time
from pathlib import Path

import streamlit as st

from web.constants import DB_FILE, DOWNLOADS_DIR, LOGS_DIR, PROJECT_ROOT
from web.utils import format_size

from media_tools.logger import get_logger
logger = get_logger('web')



# render_cleanup
"""渲染清理与备份页面"""
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
        from media_tools.douyin.core.cleaner import clean_deleted_videos

        deleted, _ = clean_deleted_videos(auto_confirm=True)
        return deleted > 0
    except Exception:
        logger.exception('发生异常')
        return False


def _get_db_stats() -> dict | None:
    """获取数据库统计信息"""
    try:
        from media_tools.douyin.core.db_helper import execute_query

        video_count = execute_query("SELECT COUNT(*) FROM video_metadata")[0][0]
        user_count = execute_query("SELECT COUNT(*) FROM user_info_web")[0][0]
        return {"video_count": video_count, "user_count": user_count}
    except Exception:
        logger.exception('发生异常')
        return None


def _clean_db_records() -> tuple[int, int]:
    """清理过期数据库记录，返回 (清理数量, 跳过数量)"""
    try:
        from media_tools.douyin.core.cleaner import clean_deleted_videos

        cleaned, skipped = clean_deleted_videos(auto_confirm=True)
        return cleaned, skipped
    except Exception as e:
        logger.exception('发生异常')
        st.error(f"清理失败: {e}")
        return 0, 0


def _clean_old_logs() -> None:
    """清理旧日志文件"""
    cutoff = time.time() - 30 * 24 * 3600

    for f in LOGS_DIR.glob("*.log"):
        if f.stat().st_mtime < cutoff:
            f.unlink()


def _render_backup_restore() -> None:
    """备份/恢复功能"""
    st.subheader("💾 数据备份与恢复")

    st.markdown(
        """
    **备份内容包含：**
    - 关注列表 (`config/following.json`)
    - 配置文件 (`config/config.yaml`)
    - 数据库 (`douyin_users.db`)
    - 认证文件 (`.auth/` 目录)
    """
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**备份数据**")
        if st.button("📦 创建备份", type="primary", use_container_width=True):
            with st.spinner("正在创建备份..."):
                ok, backup_path = _create_backup()
                if ok:
                    st.success(f"✅ 备份已创建: {backup_path}")
                else:
                    st.error("备份失败")

    with col2:
        st.markdown("**恢复数据**")
        uploaded = st.file_uploader("上传备份文件", type=["zip", "tar.gz"])
        if uploaded and st.button("📥 恢复数据", type="secondary", use_container_width=True):
            st.warning("⚠️ 恢复操作将覆盖当前数据，确定继续？")
            if st.button("✅ 确认恢复", type="primary"):
                st.info("恢复功能开发中...")


def _create_backup() -> tuple[bool, str]:
    """创建备份

    Returns:
        tuple: (success, backup_path)
    """
    import zipfile
    from datetime import datetime

    try:
        from web.constants import PROJECT_ROOT

        backup_dir = PROJECT_ROOT / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = backup_dir / f"media_tools_backup_{timestamp}.zip"

        items_to_backup = [
            ("config", "config"),
            (".auth", ".auth"),
            ("douyin_users.db", "douyin_users.db"),
        ]

        with zipfile.ZipFile(backup_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item_path, arc_name in items_to_backup:
                path = PROJECT_ROOT / item_path
                if path.exists():
                    if path.is_file():
                        zipf.write(path, arc_name)
                    elif path.is_dir():
                        for file_path in path.rglob("*"):
                            if file_path.is_file():
                                arc_path = f"{arc_name}/{file_path.relative_to(path)}"
                                zipf.write(file_path, arc_path)

        return True, str(backup_filename)
    except Exception as e:
        logger.exception('发生异常')
        import logging

        logging.error(f"备份失败: {e}")
        return False, ""
st.title("🗑️ 清理与备份")
st.caption("释放本地空间、清理历史记录，并备份关键配置与数据。")

tab1, tab2, tab3, tab4 = st.tabs(["🎬 视频清理", "🗄️ 数据库清理", "📝 日志清理", "💾 备份/恢复"])

with tab1:
    _render_video_cleanup()
with tab2:
    _render_db_cleanup()
with tab3:
    _render_log_cleanup()
with tab4:
    _render_backup_restore()


