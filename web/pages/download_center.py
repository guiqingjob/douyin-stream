"""
下载中心页面
"""

import logging
import time
import uuid

import streamlit as st

from web.components.progress_display import render_task_history, render_task_progress
from web.components.task_queue import load_task_state, run_task_in_background, update_task_progress
from web.components.ui_patterns import (
    render_empty_state,
    render_highlight_card,
    render_page_header,
    render_summary_metrics,
    render_table_section,
    render_cta_section,
)
from web.constants import DOWNLOADS_DIR, PAGE_TRANSCRIBE
from web.utils import format_size, format_timestamp

from media_tools.logger import get_logger
logger = get_logger('web')



# render_download_center
"""渲染下载中心页面"""
def _render_new_download() -> None:
    """创建下载任务"""
    st.subheader("🚀 创建素材获取任务")
    st.caption("先决定是临时下载一个链接，还是按关注列表批量拉取。")

    mode = st.radio(
        "获取方式",
        ["🔗 粘贴链接下载", "👥 从关注列表批量拉取"],
        horizontal=True,
    )

    if "链接" in mode:
        _render_single_download()
    else:
        _render_batch_download()


def _render_single_download() -> None:
    """单链接下载"""
    st.markdown("**适合临时验证、单条采集或快速拿到一个样例视频。**")

    url = st.text_input(
        "抖音视频 / 博主链接",
        placeholder="https://www.douyin.com/video/... 或 https://www.douyin.com/user/...",
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        max_count = st.number_input("最多下载数量", min_value=1, max_value=9999, value=3)
    with col2:
        st.caption("如果粘贴的是博主主页链接，这里表示最多拉取多少个视频。")

    if st.button("🚀 开始下载", type="primary", key="start_single_download"):
        if not url:
            st.warning("请输入链接")
            return

        _start_download_task(url, max_count)


def _render_batch_download() -> None:
    """批量下载关注来源"""
    st.markdown("**适合日常更新素材库：按已保存的来源逐个拉取内容。**")

    try:
        from media_tools.douyin.utils.following import list_users

        users = list_users()
        source_count = len(users)
        st.info(f"当前已配置 **{source_count}** 个来源")
    except Exception as e:
        logger.exception('发生异常')
        source_count = 0
        st.warning(f"无法读取关注列表：{e}")

    col1, col2 = st.columns([1, 2])
    with col1:
        max_per_user = st.number_input("每个来源最多下载", min_value=1, max_value=9999, value=5)
    with col2:
        st.caption("系统会遍历关注列表，按来源逐个下载。")

    if st.button("🚀 开始批量拉取", type="primary", key="start_batch_download"):
        if source_count == 0:
            st.warning("当前没有可用来源，请先去关注管理添加来源。")
            return
        _start_batch_download_task(max_per_user)


@st.fragment(run_every=2)
def _poll_download_task() -> None:
    is_running = render_task_progress(empty_message="当前没有正在执行的下载任务")
    if not is_running:
        st.rerun()

def _render_current_task() -> None:
    """当前任务"""
    st.subheader("📌 当前任务")
    st.caption("当前版本以单任务后台执行为主，适合先跑通一个任务再继续下一步。")

    state = load_task_state()
    is_active = state is not None and state.get("status") in {"pending", "running"}

    if is_active:
        _poll_download_task()
        return

    render_task_progress(empty_message="当前没有正在执行的下载任务")
    
    if state is None or state.get("status") not in {"success", "failed"}:
        render_empty_state(
            "当前没有下载任务在执行。",
            "通常下一步是去素材库确认结果，或者直接进入转写中心继续处理。",
            icon="📭"
        )
        if render_cta_section(
            "下一步", 
            "把刚下载的视频变成文稿", 
            "🎙️ 去转写中心", 
            "go_transcribe_from_download"
        ):
            st.switch_page("web/pages/transcribe_center.py")


def _start_download_task(url: str, max_count: int) -> None:
    """启动下载任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 下载任务已提交 (ID: {task_id})")

    def _worker():
        from media_tools.douyin.core.downloader import download_by_url

        update_task_progress(0.1, "正在解析链接...")
        result = download_by_url(url, max_counts=max_count)
        update_task_progress(1.0, "素材下载完成")
        return result

    run_task_in_background(
        _worker,
        task_id,
        "download",
        f"下载素材: {url[:50]}...",
        success_message="素材已下载到本地素材库",
    )
    st.rerun()


def _start_batch_download_task(max_per_user: int) -> None:
    """启动批量下载任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 批量拉取任务已提交 (ID: {task_id})")

    def _worker():
        from media_tools.douyin.core.downloader import download_by_url
        from media_tools.douyin.utils.following import list_users

        users = list_users()
        if not users:
            raise ValueError("关注列表为空，请先添加来源")

        total = len(users)
        success_list = []
        failed_list = []

        for i, user in enumerate(users):
            progress = (i + 1) / total
            nickname = user.get("nickname", user.get("name", user.get("uid", "未知用户")))
            update_task_progress(progress, f"正在拉取 {nickname} ({i + 1}/{total})")

            sec_user_id = user.get("sec_user_id", "")
            uid = user.get("uid", "")
            
            # 如果没有 sec_user_id，尝试使用 uid 构建 URL
            if sec_user_id and sec_user_id.startswith("MS4w"):
                url = f"https://www.douyin.com/user/{sec_user_id}"
            elif uid:
                url = f"https://www.douyin.com/user/{uid}"
            else:
                failed_list.append({"user": nickname, "error": "缺少用户标识 (uid/sec_user_id)"})
                continue

            try:
                result = download_by_url(url, max_counts=max_per_user)
                if isinstance(result, dict) and result.get('success'):
                    success_list.append(nickname)
                else:
                    failed_list.append({"user": nickname, "error": "下载失败 (无可用新视频或访问受限)"})
            except Exception as e:
                logger.exception('发生异常')
                failed_list.append({"user": nickname, "error": str(e)})
                logging.warning(f"下载异常: {nickname} - {e}")

        # 只要有成功或部分成功，就不抛出致命异常，而是正常返回结果对象
        if len(failed_list) == total and total > 0:
            raise RuntimeError(f"全部 {total} 个用户下载失败，请检查网络或 Cookie 状态。")
            
        return {
            "success_count": len(success_list),
            "failed_count": len(failed_list),
            "success_list": success_list,
            "failed_list": failed_list,
            "total_users": total
        }

    run_task_in_background(
        _worker,
        task_id,
        "batch_download",
        f"批量拉取素材: {max_per_user} 个/来源",
        success_message="批量素材拉取完成",
    )
    st.rerun()
render_page_header("📥 下载中心", "把抖音链接或关注来源，变成本地素材库中的视频文件。")

col1, col2 = st.columns([2, 1], gap='large')

with col1:
    _render_new_download()
with col2:
    _render_current_task()
st.divider()
st.subheader("📜 最近任务历史")
st.caption("统一查看最近下载相关任务的结果与状态变化。")
render_task_history()

