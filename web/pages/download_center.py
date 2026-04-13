"""
下载中心页面
"""

import streamlit as st
import uuid
import logging
import time
from pathlib import Path

from web.constants import DOWNLOADS_DIR
from web.components.progress_display import render_task_progress
from web.components.task_queue import run_task_in_background


def render_download_center() -> None:
    """渲染下载中心页面"""
    st.title("📥 下载中心")
    
    tab1, tab2, tab3 = st.tabs(["✨ 新建下载", "📋 任务队列", "📁 已下载管理"])
    
    with tab1:
        _render_new_download()
    with tab2:
        _render_task_queue()
    with tab3:
        _render_downloaded_files()
    
    # 显示当前任务进度
    st.divider()
    is_running = render_task_progress()
    
    # 任务历史按钮
    if st.button("📜 查看任务历史", key="show_task_history_download_center"):
        from web.components.progress_display import render_task_history
        render_task_history()
    
    # 如果有任务在运行，自动刷新
    if is_running:
        time.sleep(2)
        st.rerun()


def _render_new_download() -> None:
    """新建下载"""
    st.subheader("✨ 新建下载任务")
    
    # 下载模式选择
    mode = st.radio(
        "下载模式",
        ["🔗 单链接下载", "👥 批量下载关注"],
        horizontal=True,
    )
    
    if "单链接" in mode:
        _render_single_download()
    else:
        _render_batch_download()


def _render_single_download() -> None:
    """单链接下载"""
    st.markdown("**通过抖音链接下载视频**")
    
    url = st.text_input(
        "抖音视频/博主链接",
        placeholder="https://www.douyin.com/video/... 或 https://www.douyin.com/user/...",
    )
    
    col1, col2 = st.columns([1, 2])
    with col1:
        max_count = st.number_input("最多下载数量", min_value=1, max_value=9999, value=3)
    
    if st.button("🚀 开始下载", type="primary"):
        if not url:
            st.warning("请输入链接")
            return
        
        _start_download_task(url, max_count)


def _render_batch_download() -> None:
    """批量下载关注"""
    st.markdown("**批量下载已关注的博主**")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        max_per_user = st.number_input("每个博主最多下载", min_value=1, max_value=9999, value=5)
    
    # 显示关注列表统计
    try:
        from media_tools.douyin.utils.following import list_users
        users = list_users()
        st.info(f"📊 当前关注列表有 **{len(users)}** 个博主")
    except Exception:
        pass
    
    if st.button("🚀 开始批量下载", type="primary"):
        _start_batch_download_task(max_per_user)


def _render_task_queue() -> None:
    """任务队列"""
    st.subheader("📋 下载任务队列")
    st.info("💡 任务队列功能开发中... 当前仅支持单任务运行。")
    
    # 显示当前任务
    render_task_progress()


def _render_downloaded_files() -> None:
    """已下载管理"""
    st.subheader("📁 已下载文件管理")
    
    if DOWNLOADS_DIR.exists():
        video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
        total_size = sum(f.stat().st_size for f in video_files)
        
        from web.utils import format_size
        st.info(f"共 **{len(video_files)}** 个视频文件，占用 **{format_size(total_size)}**")
        
        if video_files:
            # 显示文件列表（前 20 个）
            st.dataframe(
                [
                    {
                        "文件名": f.name[:50],
                        "大小": format_size(f.stat().st_size),
                        "修改时间": f.stat().st_mtime,
                    }
                    for f in sorted(video_files, key=lambda x: x.stat().st_mtime, reverse=True)[:20]
                ],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("downloads 目录不存在")


def _start_download_task(url: str, max_count: int) -> None:
    """启动下载任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 任务已提交 (ID: {task_id})")
    
    def _worker():
        from web.components.task_queue import update_task_progress, mark_task_success, mark_task_failed
        
        try:
            from media_tools.douyin.core.downloader import download_by_url
            
            update_task_progress(0.1, "正在解析链接...")
            result = download_by_url(url, max_counts=max_count)
            update_task_progress(1.0, "下载完成")
            mark_task_success(result)
        except Exception as e:
            mark_task_failed(str(e))
    
    run_task_in_background(_worker, task_id, "download", f"下载: {url[:50]}...")
    st.rerun()


def _start_batch_download_task(max_per_user: int) -> None:
    """启动批量下载任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 批量任务已提交 (ID: {task_id})")
    
    def _worker():
        from web.components.task_queue import update_task_progress, mark_task_success, mark_task_failed
        
        try:
            from media_tools.douyin.utils.following import list_users
            from media_tools.douyin.core.downloader import download_by_url
            
            users = list_users()
            if not users:
                mark_task_failed("关注列表为空")
                return
            
            total = len(users)
            success_list = []
            failed_list = []
            
            for i, user in enumerate(users):
                progress = (i + 1) / total
                nickname = user.get("nickname", user.get("name", user.get("uid", "")))
                update_task_progress(progress, f"正在下载 {nickname} ({i+1}/{total})")
                
                sec_user_id = user.get("sec_user_id", "")
                if sec_user_id:
                    url = f"https://www.douyin.com/user/{sec_user_id}"
                    try:
                        download_by_url(url, max_counts=max_per_user)
                        success_list.append(nickname)
                    except Exception as e:
                        failed_list.append({"user": nickname, "error": str(e)})
                        logging.warning(f"下载失败: {nickname} - {e}")
            
            result = {
                "total_users": total,
                "success_count": len(success_list),
                "failed_count": len(failed_list),
                "success_list": success_list,
                "failed_list": failed_list,
            }
            mark_task_success(result)
        except Exception as e:
            mark_task_failed(str(e))
    
    run_task_in_background(_worker, task_id, "batch_download", f"批量下载 {max_per_user} 个/博主")
    st.rerun()
