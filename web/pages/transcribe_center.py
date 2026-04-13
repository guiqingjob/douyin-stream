"""
转写中心页面
"""

import streamlit as st
import uuid
import logging
import time
import asyncio
from pathlib import Path

from web.constants import DOWNLOADS_DIR, TRANSCRIPTS_DIR, TEMP_UPLOADS_DIR, QWEN_AUTH_PATH
from web.components.progress_display import render_task_progress


def render_transcribe_center() -> None:
    """渲染转写中心页面"""
    st.title("🎙️ 转写中心")
    
    tab1, tab2, tab3 = st.tabs(["✨ 新建转写", "📋 任务队列", "📄 文稿管理"])
    
    with tab1:
        _render_new_transcribe()
    with tab2:
        _render_task_queue()
    with tab3:
        _render_transcripts()
    
    # 显示当前任务进度
    st.divider()
    is_running = render_task_progress()
    
    # 任务历史按钮
    if st.button("📜 查看任务历史", key="show_task_history_transcribe_center"):
        from web.components.progress_display import render_task_history
        render_task_history()
    
    # 如果有任务在运行，自动刷新
    if is_running:
        time.sleep(2)
        st.rerun()


def _render_new_transcribe() -> None:
    """新建转写"""
    st.subheader("✨ 新建转写任务")
    
    mode = st.radio(
        "转写模式",
        ["📄 单文件转写", "📂 批量转写"],
        horizontal=True,
    )
    
    if "单文件" in mode:
        _render_single_transcribe()
    else:
        _render_batch_transcribe()


def _render_single_transcribe() -> None:
    """单文件转写"""
    st.markdown("**上传视频/音频文件进行转写**")
    
    uploaded = st.file_uploader(
        "选择文件",
        type=["mp4", "mp3", "wav", "m4a", "aac", "flac", "ogg"],
    )
    
    if uploaded:
        st.success(f"✅ 文件已上传: {uploaded.name}")
        
        if st.button("🚀 开始转写", type="primary"):
            TEMP_UPLOADS_DIR.mkdir(exist_ok=True)
            temp_path = TEMP_UPLOADS_DIR / uploaded.name
            with open(temp_path, "wb") as f:
                f.write(uploaded.getbuffer())
            
            _start_transcribe_task(str(temp_path))


def _render_batch_transcribe() -> None:
    """批量转写"""
    st.markdown("**批量转写 downloads 目录下的所有视频**")
    
    if DOWNLOADS_DIR.exists():
        video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
        st.info(f"📊 发现 **{len(video_files)}** 个视频文件")
        
        if st.button("🚀 开始批量转写", type="primary"):
            _start_batch_transcribe_task()
    else:
        st.warning("downloads 目录不存在")


def _render_task_queue() -> None:
    """任务队列"""
    st.subheader("📋 转写任务队列")
    st.info("💡 任务队列功能开发中... 当前仅支持单任务运行。")
    
    render_task_progress()


def _render_transcripts() -> None:
    """文稿管理"""
    st.subheader("📄 已转写文稿")
    
    if TRANSCRIPTS_DIR.exists():
        md_files = list(TRANSCRIPTS_DIR.rglob("*.md"))
        st.info(f"共 **{len(md_files)}** 个文稿文件")
        
        if md_files:
            st.dataframe(
                [
                    {
                        "文件名": f.name[:50],
                        "大小": _format_size(f.stat().st_size),
                        "修改时间": f.stat().st_mtime,
                    }
                    for f in sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True)[:20]
                ],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("transcripts 目录不存在")


def _start_transcribe_task(file_path: str) -> None:
    """启动转写任务"""
    from web.components.task_queue import run_task_in_background
    
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 转写任务已提交 (ID: {task_id})")
    
    def _worker():
        from web.components.task_queue import update_task_progress, mark_task_success, mark_task_failed
        
        try:
            update_task_progress(0.1, "正在初始化转写...")
            
            from media_tools.pipeline.orchestrator_v2 import create_orchestrator
            from media_tools.pipeline.config import load_pipeline_config
            
            config = load_pipeline_config()
            orchestrator = create_orchestrator(config)
            
            update_task_progress(0.3, "正在上传文件...")
            result = asyncio.run(orchestrator.transcribe_with_retry(file_path))
            
            update_task_progress(1.0, "转写完成")
            mark_task_success(result)
            
            # 清理临时文件
            try:
                Path(file_path).unlink()
            except Exception:
                pass
        except Exception as e:
            mark_task_failed(str(e))
    
    run_task_in_background(_worker, task_id, "transcribe", f"转写: {Path(file_path).name}")
    st.rerun()


def _start_batch_transcribe_task() -> None:
    """启动批量转写任务"""
    from web.components.task_queue import run_task_in_background
    
    task_id = str(uuid.uuid4())[:8]
    st.info(f"🚀 批量转写任务已提交 (ID: {task_id})")
    
    def _worker():
        from web.components.task_queue import update_task_progress, mark_task_success, mark_task_failed
        
        try:
            video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
            total = len(video_files)
            
            success_list = []
            failed_list = []
            
            for i, video_file in enumerate(video_files):
                progress = (i + 1) / total
                update_task_progress(progress, f"正在转写 {video_file.name} ({i+1}/{total})")
                
                try:
                    from media_tools.pipeline.orchestrator_v2 import create_orchestrator
                    from media_tools.pipeline.config import load_pipeline_config
                    
                    config = load_pipeline_config()
                    orchestrator = create_orchestrator(config)
                    asyncio.run(orchestrator.transcribe_with_retry(str(video_file)))
                    success_list.append(video_file.name)
                except Exception as e:
                    failed_list.append({"file": video_file.name, "error": str(e)})
                    logging.warning(f"转写失败: {video_file.name} - {e}")
            
            result = {
                "total_files": total,
                "success_count": len(success_list),
                "failed_count": len(failed_list),
                "success_list": success_list,
                "failed_list": failed_list,
            }
            mark_task_success(result)
        except Exception as e:
            mark_task_failed(str(e))
    
    run_task_in_background(_worker, task_id, "batch_transcribe", f"批量转写 {task_id}")
    st.rerun()


def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
