"""
下载任务页面
"""

import streamlit as st
import time
from pathlib import Path

from web.components.progress_display import render_task_progress
from web.components.task_queue import run_task_in_background


def render_download() -> None:
    """渲染下载任务页面"""
    st.title("📥 下载任务")

    tab1, tab2, tab3 = st.tabs(["🔗 单链接下载", "👥 批量下载关注", "📊 检查更新"])

    with tab1:
        _render_single_download()
    with tab2:
        _render_batch_download()
    with tab3:
        _render_check_updates()
    
    # 显示任务进度
    st.divider()
    render_task_progress()


def _render_single_download() -> None:
    """单链接下载"""
    st.subheader("🔗 通过链接下载视频")

    url = st.text_input(
        "抖音视频/博主链接",
        placeholder="https://www.douyin.com/video/... 或 https://www.douyin.com/user/...",
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        max_count = st.number_input("每个博主最多下载数量", min_value=1, max_value=9999, value=3)

    if st.button("开始下载", type="primary"):
        if not url:
            st.warning("请输入链接")
            return

        _start_download_task(url, max_count)


def _render_batch_download() -> None:
    """批量下载关注"""
    st.subheader("👥 批量下载已关注的博主")

    max_per_user = st.number_input(
        "每位博主最多下载数量",
        min_value=1,
        max_value=9999,
        value=3,
    )

    if st.button("下载所有关注", type="primary"):
        _start_batch_download_task(max_per_user)


def _render_check_updates() -> None:
    """检查更新"""
    st.subheader("📊 检查博主更新")

    if st.button("检查更新", type="primary"):
        with st.spinner("正在检查..."):
            updates = _check_updates()
            if updates:
                st.success(f"发现 {len(updates)} 位博主有更新")
                for uid, info in updates.items():
                    nickname = info.get("nickname", uid)
                    new_count = info.get("new_count", 0)
                    st.info(f"📌 {nickname}: {new_count} 个新视频")
            else:
                st.info("所有博主均为最新")


def _start_download_task(url: str, max_count: int) -> None:
    """启动下载任务"""
    import uuid

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
    import uuid
    import logging

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

            # 生成统计报告
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


def _check_updates() -> dict:
    """检查更新"""
    try:
        from media_tools.douyin.core.update_checker import check_all_updates

        return check_all_updates()
    except Exception:
        return {}
