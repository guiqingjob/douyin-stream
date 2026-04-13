"""
清理与备份页面
"""

import time
from pathlib import Path

import streamlit as st

from web.constants import DB_FILE, DOWNLOADS_DIR, LOGS_DIR, PROJECT_ROOT
from web.components.ui_patterns import render_page_header, render_danger_zone
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

        if render_danger_zone(
            "清理已删除视频的数据库记录",
            "同步本地文件和数据库状态，删除数据库中存在但本地已删除的视频记录。",
            "清理记录",
            "clean_db_video"
        ):
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

        if render_danger_zone(
            "清理过期数据库记录",
            "彻底删除无效的、不再存在的视频记录，释放数据库空间。",
            "清理记录",
            "clean_db_records"
        ):
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

        if render_danger_zone(
            "清理 30 天前的旧日志",
            "自动删除 30 天前的历史日志文件以释放磁盘空间。",
            "清理日志",
            "clean_logs"
        ):
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
        uploaded = st.file_uploader("上传备份文件", type=["zip"])
        if uploaded and st.button("📥 恢复数据", type="secondary", use_container_width=True):
            st.warning("⚠️ 恢复操作将覆盖当前数据，确定继续？")
            if st.button("✅ 确认恢复", type="primary"):
                with st.spinner("正在恢复数据..."):
                    ok, msg = _restore_backup(uploaded)
                    if ok:
                        st.success(f"✅ {msg}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"恢复失败: {msg}")


def _restore_backup(uploaded_file) -> tuple[bool, str]:
    """从上传的 zip 文件中恢复备份数据
    
    Returns:
        tuple: (success, message)
    """
    import zipfile
    import shutil
    import tempfile
    
    try:
        from web.constants import PROJECT_ROOT
        
        # 1. 创建临时目录解压
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "uploaded_backup.zip"
        
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # 2. 解压文件
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # 3. 验证并覆盖现有目录
        restored_items = []
        for item in ["config", ".auth", "douyin_users.db"]:
            source_item = extract_dir / item
            target_item = PROJECT_ROOT / item
            
            if source_item.exists():
                # 删除原有数据
                if target_item.exists():
                    if target_item.is_dir():
                        shutil.rmtree(target_item)
                    else:
                        target_item.unlink()
                        
                # 移动新数据
                if source_item.is_dir():
                    shutil.copytree(source_item, target_item)
                else:
                    shutil.copy2(source_item, target_item)
                restored_items.append(item)
                
        # 4. 清理临时目录
        shutil.rmtree(temp_dir)
        
        if not restored_items:
            return False, "备份文件中未找到有效的配置或数据目录。"
            
        return True, f"已成功恢复: {', '.join(restored_items)}。请重启应用以完全生效。"
        
    except zipfile.BadZipFile:
        return False, "上传的文件不是有效的 ZIP 压缩包。"
    except Exception as e:
        logger.exception("恢复备份时发生异常")
        return False, str(e)
    finally:
        # 确保清理临时目录
        if 'temp_dir' in locals() and temp_dir.exists():
            shutil.rmtree(temp_dir)


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
render_page_header("🗑️ 清理与备份", "释放本地空间、清理历史记录，并备份关键配置与数据。")

tab1, tab2, tab3, tab4 = st.tabs(["🎬 视频清理", "🗄️ 数据库清理", "📝 日志清理", "💾 备份/恢复"])

with tab1:
    _render_video_cleanup()
with tab2:
    _render_db_cleanup()
with tab3:
    _render_log_cleanup()
with tab4:
    _render_backup_restore()

