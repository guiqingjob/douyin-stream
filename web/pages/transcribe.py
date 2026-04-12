"""
转写任务页面
"""

import streamlit as st
import uuid
from pathlib import Path

from web.components.progress_display import render_task_progress
from web.components.task_queue import run_task_in_background


def render_transcribe() -> None:
    """渲染转写任务页面"""
    st.title("🎙️ 转写任务")

    tab1, tab2 = st.tabs(["📄 单文件转写", "📂 批量转写"])

    with tab1:
        _render_single_transcribe()
    with tab2:
        _render_batch_transcribe()


def _render_single_transcribe() -> None:
    """单文件转写"""
    st.subheader("📄 上传视频/音频文件进行转写")

    uploaded = st.file_uploader(
        "选择文件",
        type=["mp4", "mp3", "wav", "m4a", "aac", "flac", "ogg"],
    )

    if uploaded:
        # 保存到临时目录
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / uploaded.name
        with open(temp_path, "wb") as f:
            f.write(uploaded.getbuffer())

        st.success(f"文件已上传: {uploaded.name} ({uploaded.size / 1024 / 1024:.2f} MB)")

        if st.button("开始转写", type="primary"):
            _start_transcribe_task(str(temp_path))


def _render_batch_transcribe() -> None:
    """批量转写"""
    st.subheader("📂 批量转写本地文件")

    # 扫描下载目录
    downloads_dir = Path("downloads")
    transcripts_dir = Path("transcripts")

    if downloads_dir.exists():
        video_files = list(downloads_dir.rglob("*.mp4"))
        audio_files = (
            list(downloads_dir.rglob("*.mp3"))
            + list(downloads_dir.rglob("*.wav"))
            + list(downloads_dir.rglob("*.m4a"))
        )
        total_files = len(video_files) + len(audio_files)

        st.info(f"发现 {total_files} 个音视频文件")

        if st.button(f"批量转写全部 {total_files} 个文件", type="primary"):
            _start_batch_transcribe_task(video_files + audio_files)
    else:
        st.warning("downloads 目录不存在，请先下载视频")


def _start_transcribe_task(file_path: str) -> None:
    """启动转写任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 转写任务已提交 (ID: {task_id})")

    def _worker():
        from web.components.task_queue import update_task_progress, mark_task_success, mark_task_failed

        try:
            import asyncio
            from media_tools.pipeline.orchestrator_v2 import create_orchestrator
            from media_tools.pipeline.config import load_pipeline_config

            update_task_progress(0.1, "正在初始化...")

            config = load_pipeline_config()
            auth_path = Path(".auth/qwen-storage-state.json")

            if not auth_path.exists():
                mark_task_failed("Qwen 认证文件不存在，请先进行认证")
                return

            orchestrator = create_orchestrator(
                config=config,
                auth_state_path=str(auth_path),
            )

            update_task_progress(0.3, "正在上传文件...")

            async def _run():
                return await orchestrator.transcribe_with_retry(Path(file_path))

            result = asyncio.run(_run())
            update_task_progress(1.0, "转写完成")
            mark_task_success({"file": file_path, "status": result.status if hasattr(result, "status") else "success"})
        except Exception as e:
            mark_task_failed(str(e))

    run_task_in_background(_worker, task_id, "transcribe", f"转写: {Path(file_path).name}")
    st.rerun()


def _start_batch_transcribe_task(files: list[Path]) -> None:
    """启动批量转写任务"""
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 批量转写任务已提交 (ID: {task_id})")

    def _worker():
        from web.components.task_queue import update_task_progress, mark_task_success, mark_task_failed

        try:
            import asyncio
            from media_tools.pipeline.orchestrator_v2 import create_orchestrator
            from media_tools.pipeline.config import load_pipeline_config

            config = load_pipeline_config()
            auth_path = Path(".auth/qwen-storage-state.json")

            if not auth_path.exists():
                mark_task_failed("Qwen 认证文件不存在")
                return

            orchestrator = create_orchestrator(
                config=config,
                auth_state_path=str(auth_path),
            )

            total = len(files)
            for i, f in enumerate(files):
                progress = (i + 1) / total
                update_task_progress(progress, f"正在转写 {f.name} ({i+1}/{total})")

                async def _run():
                    return await orchestrator.transcribe_with_retry(f)

                try:
                    asyncio.run(_run())
                except Exception:
                    pass  # 单个失败不影响其他

            mark_task_success({"total_files": total})
        except Exception as e:
            mark_task_failed(str(e))

    run_task_in_background(_worker, task_id, "batch_transcribe", f"批量转写 {len(files)} 个文件")
    st.rerun()
