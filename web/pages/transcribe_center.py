"""
转写中心页面
"""

import asyncio
import logging
import time
import uuid
from pathlib import Path

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
from web.constants import DOWNLOADS_DIR, QWEN_AUTH_PATH, TEMP_UPLOADS_DIR, TRANSCRIPTS_DIR
from web.utils import format_size, format_timestamp

from media_tools.logger import get_logger
logger = get_logger('web')



# render_transcribe_center
"""渲染转写中心页面"""
def _render_new_transcribe() -> None:
    """发起转写"""
    st.subheader("🚀 发起文稿生成任务")
    st.caption("可以上传单个文件，也可以直接处理已经进入素材库的视频。")

    mode = st.radio(
        "输入方式",
        ["📄 上传文件转写", "📂 处理素材库中的视频"],
        horizontal=True,
    )

    if "上传" in mode:
        _render_single_transcribe()
    else:
        _render_batch_transcribe()


def _render_single_transcribe() -> None:
    """单文件转写"""
    st.markdown("**适合临时转写一个本地文件，快速验证输出效果。**")

    uploaded = st.file_uploader(
        "选择视频 / 音频文件",
        type=["mp4", "mp3", "wav", "m4a", "aac", "flac", "ogg"],
    )

    if not uploaded:
        return

    st.success(f"✅ 文件已上传: {uploaded.name} ({uploaded.size / 1024 / 1024:.2f} MB)")
    st.caption("输出结果会进入 `transcripts/` 文稿库。")

    if st.button("🚀 开始转写", type="primary", key="start_single_transcribe"):
        TEMP_UPLOADS_DIR.mkdir(exist_ok=True)
        temp_path = TEMP_UPLOADS_DIR / uploaded.name
        with open(temp_path, "wb") as f:
            f.write(uploaded.getbuffer())

        _start_transcribe_task(str(temp_path))


def _render_batch_transcribe() -> None:
    """批量转写素材库中的视频"""
    st.markdown("**适合把已经下载好的素材批量转成文稿。**")

    if not DOWNLOADS_DIR.exists():
        render_empty_state("素材目录不存在。", "先去下载中心获取一批素材，再回来批量转写。", icon="📂")
        return

    video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
    total_size = sum(f.stat().st_size for f in video_files)

    render_summary_metrics(
        [
            {"label": "待处理素材", "value": len(video_files)},
            {"label": "素材总大小", "value": format_size(total_size)},
            {"label": "输出目录", "value": "transcripts/"},
        ]
    )

    if not video_files:
        render_empty_state("素材库里还没有视频。", "先去下载中心获取素材，再回来生成文稿。")
        return

    st.caption("系统会遍历素材库中的视频文件，逐个生成文稿。")
    if st.button("🚀 开始批量转写", type="primary", key="start_batch_transcribe"):
        _start_batch_transcribe_task()


@st.fragment(run_every=2)
def _poll_transcribe_task() -> None:
    is_running = render_task_progress(empty_message="当前没有正在执行的转写任务")
    if not is_running:
        st.rerun()

def _render_current_task() -> None:
    """当前任务"""
    st.subheader("📌 当前任务")
    st.caption("当前版本以单任务后台执行为主，任务完成后结果会写入文稿库。")

    state = load_task_state()
    is_active = state is not None and state.get("status") in {"pending", "running"}

    if is_active:
        _poll_transcribe_task()
        return

    render_task_progress(empty_message="当前没有正在执行的转写任务")

    if state is None or state.get("status") not in {"success", "failed"}:
        render_empty_state(
            "当前没有转写任务在执行。", 
            "如果已经上传文件或准备好素材，可以立即发起新的文稿生成任务。",
            icon="⏳"
        )
        if render_cta_section(
            "没有素材？", 
            "前往下载中心，获取抖音视频素材。", 
            "📥 去下载中心", 
            "go_download_from_transcribe"
        ):
            st.switch_page("web/pages/download_center.py")


def _start_transcribe_task(file_path: str) -> None:
    """启动单文件转写任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 转写任务已提交 (ID: {task_id})")

    def _worker():
        if not QWEN_AUTH_PATH.exists():
            raise ValueError("Qwen 认证文件不存在，请先完成认证")

        update_task_progress(0.1, "正在初始化转写...")

        from media_tools.pipeline.config import load_pipeline_config
        from media_tools.pipeline.orchestrator_v2 import create_orchestrator

        config = load_pipeline_config()
        orchestrator = create_orchestrator(config)

        async def _run_transcribe():
            return await orchestrator.transcribe_with_retry(file_path)

        update_task_progress(0.3, "正在上传文件...")
        result = asyncio.run(_run_transcribe())

        update_task_progress(1.0, "文稿生成完成")

        try:
            Path(file_path).unlink()
        except Exception:
            logger.exception('发生异常')
            pass

        return result

    run_task_in_background(
        _worker,
        task_id,
        "transcribe",
        f"生成文稿: {Path(file_path).name}",
        success_message="文稿已写入 transcripts/",
    )
    st.rerun()


def _start_batch_transcribe_task() -> None:
    """启动批量转写任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 批量转写任务已提交 (ID: {task_id})")

    def _worker():
        if not QWEN_AUTH_PATH.exists():
            raise ValueError("Qwen 认证文件不存在，请先完成认证")

        video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
        total = len(video_files)
        if total == 0:
            raise ValueError("素材库为空，请先下载视频")

        success_list = []
        failed_list = []

        from media_tools.pipeline.config import load_pipeline_config
        from media_tools.pipeline.orchestrator_v2 import create_orchestrator

        config = load_pipeline_config()
        orchestrator = create_orchestrator(config)

        async def _run_batch():
            for i, video_file in enumerate(video_files):
                progress = (i + 1) / total
                update_task_progress(progress, f"正在生成文稿 {video_file.name} ({i + 1}/{total})")

                try:
                    await orchestrator.transcribe_with_retry(str(video_file))
                    success_list.append(video_file.name)
                except Exception as e:
                    logger.exception('发生异常')
                    failed_list.append({"file": video_file.name, "error": str(e)})
                    logging.warning(f"转写失败: {video_file.name} - {e}")

        asyncio.run(_run_batch())

        return {
            "total_files": total,
            "success_count": len(success_list),
            "failed_count": len(failed_list),
            "success_list": success_list,
            "failed_list": failed_list,
        }

    run_task_in_background(
        _worker,
        task_id,
        "batch_transcribe",
        f"批量生成文稿: {task_id}",
        success_message="批量文稿生成完成",
    )
    st.rerun()
render_page_header("🎙️ 转写中心", "把视频或音频素材，变成可整理、可搜索、可再利用的文稿。")

col1, col2 = st.columns([2, 1], gap='large')

with col1:
    _render_new_transcribe()
with col2:
    _render_current_task()
st.divider()
st.subheader("📜 最近任务历史")
st.caption("统一查看最近转写相关任务的结果与状态变化。")
render_task_history()

