"""
转写中心页面
"""

import asyncio
import logging
import uuid
from pathlib import Path

import streamlit as st

from media_tools.logger import get_logger
from media_tools.web.components.progress_display import render_task_history, render_task_progress
from media_tools.web.components.task_queue import load_task_state, run_task_in_background, update_task_progress
from media_tools.web.components.ui_patterns import (
    render_cta_section,
    render_empty_state,
    render_page_header,
    render_summary_metrics,
)
from media_tools.transcribe.auth_state import has_qwen_auth_state
from media_tools.web.constants import TEMP_UPLOADS_DIR
from media_tools.web.services.status import get_system_status
from media_tools.web.utils import get_page_path

logger = get_logger('web')

TRANSCRIBE_TASK_TYPES = ["transcribe", "batch_transcribe"]


def _check_auth() -> bool:
    try:
        return has_qwen_auth_state()
    except Exception:
        logger.exception("检查 Qwen 认证失败")
        return False


def _render_transcribe_summary() -> dict:
    status = get_system_status()
    render_summary_metrics(
        [
            {"label": "待转写素材", "value": status["pending_transcripts"]},
            {"label": "已完成文稿", "value": status["transcripts_count"]},
            {"label": "转写认证", "value": "已就绪" if status["qwen_ok"] else "待配置"},
        ]
    )
    if not status["qwen_ok"]:
        st.warning("当前尚未配置有效的 Qwen 认证，转写任务无法正常执行。建议先去“账号与认证”页面完成配置。")
    return status


def _render_new_transcribe() -> None:
    st.subheader("① 发起文稿生成任务")
    st.caption("这里专注做“素材 → 文稿”，不再混入下载来源管理。")

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
        with open(temp_path, "wb") as file:
            file.write(uploaded.getbuffer())
        _start_transcribe_task(str(temp_path))


def _fetch_pending_assets():
    try:
        import sqlite3
        from media_tools.douyin.core.config_mgr import get_config
        db_path = get_config().get_db_path()
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT asset_id, title, duration, video_path, creator_uid
                FROM media_assets
                WHERE video_status = 'downloaded' AND transcript_status != 'completed'
                ORDER BY create_time DESC
                """
            )
            return cursor.fetchall()
    except Exception as exc:
        logger.error(f"读取待转写资产失败: {exc}")
        return []


def _render_batch_transcribe() -> None:
    st.markdown("**适合把已经下载好的素材批量转成文稿。**")

    assets = _fetch_pending_assets()
    if not assets:
        render_empty_state("素材库里没有待转写的视频。", "去下载中心获取素材，或当前视频均已转写完成。", icon="🎬")
        return

    st.success(f"已发现 **{len(assets)}** 个待处理视频。")

    asset_options = {
        f"[{a[4]}] {(a[1][:30] + '...') if a[1] and len(a[1]) > 30 else (a[1] or a[0])}": a
        for a in assets
    }

    selected_labels = st.multiselect(
        "选择要转写的视频 (默认全选)",
        options=list(asset_options.keys()),
        default=list(asset_options.keys()),
    )

    if not selected_labels:
        st.warning("请至少选择一个视频")
        return

    st.caption(f"即将对选中的 {len(selected_labels)} 个视频生成文稿。")
    if st.button("🚀 开始批量转写", type="primary", key="start_batch_transcribe"):
        selected_assets = [asset_options[label] for label in selected_labels]
        _start_batch_transcribe_task(selected_assets)


@st.fragment(run_every=2)
def _poll_transcribe_task() -> None:
    is_running = render_task_progress(
        empty_message="当前没有正在执行的转写任务",
        task_types=TRANSCRIBE_TASK_TYPES,
    )
    if not is_running:
        st.rerun()


def _render_current_task() -> None:
    st.subheader("② 当前转写任务")
    st.caption("这里只展示转写类任务，不再被下载任务状态干扰。")

    state = load_task_state(task_types=TRANSCRIBE_TASK_TYPES)
    is_active = state is not None and state.get("status") in {"pending", "running"}

    if is_active:
        _poll_transcribe_task()
        return

    render_task_progress(
        empty_message="当前没有正在执行的转写任务",
        task_types=TRANSCRIBE_TASK_TYPES,
    )

    if state is None:
        render_empty_state(
            "当前没有转写任务在执行。",
            "如果还没有素材，请先去下载中心获取视频；如果已有素材，可以直接从左侧发起转写。",
            icon="⏳",
        )
        return

    if state.get("status") in {"success", "failed", "cancelled"}:
        return

    if render_cta_section(
        "没有素材？",
        "前往下载中心，先获取抖音视频素材。",
        "📥 去下载中心",
        "go_download_from_transcribe",
    ):
        st.switch_page(get_page_path("download_center.py"))


def _start_transcribe_task(file_path: str) -> None:
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 转写任务已提交 (ID: {task_id})")

    def _worker():
        if not _check_auth():
            raise ValueError("Qwen 认证无效或未完成，请先完成认证")

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
            logger.exception('清理临时文件失败')

        return result

    run_task_in_background(
        _worker,
        task_id,
        "transcribe",
        f"生成文稿: {Path(file_path).name}",
        success_message="文稿已写入 transcripts/",
    )
    st.rerun()


def _start_batch_transcribe_task(selected_assets: list) -> None:
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 批量转写任务已提交 (ID: {task_id})")

    def _worker():
        if not _check_auth():
            raise ValueError("Qwen 认证无效或未完成，请先完成认证")

        total = len(selected_assets)
        success_list = []
        failed_list = []

        from media_tools.pipeline.config import load_pipeline_config
        from media_tools.pipeline.orchestrator_v2 import create_orchestrator
        from media_tools.douyin.core.config_mgr import get_config

        config = load_pipeline_config()
        orchestrator = create_orchestrator(config)
        downloads_path = get_config().get_download_path()

        async def _run_batch():
            for i, asset in enumerate(selected_assets):
                asset_id, title, duration, rel_path, uid = asset
                progress = (i + 1) / total
                display_name = title or asset_id
                update_task_progress(progress, f"正在生成文稿 {display_name[:30]} ({i + 1}/{total})")

                video_file = downloads_path / rel_path
                if not video_file.exists():
                    failed_list.append({"file": display_name, "error": "文件不存在"})
                    continue

                try:
                    await orchestrator.transcribe_with_retry(str(video_file))
                    success_list.append(display_name)
                except Exception as exc:
                    logger.exception('转写失败')
                    failed_list.append({"file": display_name, "error": str(exc)})
                    logging.warning(f"转写失败: {display_name} - {exc}")

        asyncio.run(_run_batch())

        if len(failed_list) == total and total > 0:
            raise RuntimeError(f"全部 {total} 个视频转写失败，请检查认证状态。")

        return {
            "success_count": len(success_list),
            "failed_count": len(failed_list),
            "success_list": success_list,
            "failed_list": failed_list,
            "total_files": total,
        }

    run_task_in_background(
        _worker,
        task_id,
        "batch_transcribe",
        f"批量生成文稿: {len(selected_assets)} 个素材",
        success_message="批量文稿生成完成",
    )
    st.rerun()


render_page_header("🎙️ 转写中心", "专注把素材变成文稿，不在这里再处理下载来源。")
status = _render_transcribe_summary()

col1, col2 = st.columns([2, 1], gap='large')
with col1:
    _render_new_transcribe()
with col2:
    _render_current_task()

st.divider()
st.subheader("③ 转写任务历史")
st.caption("仅展示转写相关任务，避免和下载任务混在一起。")
render_task_history(task_types=TRANSCRIBE_TASK_TYPES)

if status["downloads_count"] == 0 and render_cta_section(
    "还没有素材？",
    "先去下载中心拿到第一批视频，再回来批量转写。",
    "📥 去下载中心",
    "transcribe_to_download_footer",
):
    st.switch_page(get_page_path("download_center.py"))
