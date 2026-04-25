"""转写工作者 - 视频转写逻辑"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def transcribe_files(task_id: str, _progress_fn, new_files: list, display_name: str, auto_delete: bool = False):
    """转写一批视频文件，返回统计信息。使用并发加速处理。"""
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    await _progress_fn(0.6, f"下载完成，准备转写 {len(new_files)} 个视频...", stage="transcribing")
    pipeline_config = load_pipeline_config()
    orchestrator = create_orchestrator(pipeline_config, creator_folder_override=display_name)
    delete_after = auto_delete
    total = len(new_files)
    subtasks: list[dict] = []

    video_paths = [Path(f) for f in new_files]
    completed_count = 0
    success_count = 0
    failed_count = 0
    lock = asyncio.Lock()

    semaphore = asyncio.Semaphore(pipeline_config.concurrency)

    async def _process_one(video_path: Path) -> None:
        nonlocal completed_count, success_count, failed_count
        title = video_path.stem[:60]
        transcribe_ok = False
        error_msg = ""
        try:
            async with semaphore:
                result = await orchestrator.transcribe_with_retry(video_path)
                transcribe_ok = bool(getattr(result, "success", False))
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"转写失败 {video_path}: {e}")

        async with lock:
            completed_count += 1
            if transcribe_ok:
                success_count += 1
                subtasks.append({"title": title, "status": "completed"})
            else:
                failed_count += 1
                subtasks.append({"title": title, "status": "failed", "error": error_msg or "转写失败"})

            await _progress_fn(
                0.6 + 0.3 * (completed_count / total),
                f"正在转写 ({completed_count}/{total})",
                subtasks=list(subtasks),
                stage="transcribing",
            )

        if delete_after and transcribe_ok:
            try:
                video_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as e:
                logger.error(f"删除转写后视频失败: {video_path}, {e}")

    await asyncio.gather(*[_process_one(p) for p in video_paths])

    result_summary = {
        "success": success_count,
        "failed": failed_count,
        "skipped": 0,
        "total": total,
    }
    await _progress_fn(
        0.9,
        f"转写完成：成功 {success_count} 个，失败 {failed_count} 个",
        result_summary=result_summary,
        subtasks=subtasks,
        stage="transcribing",
    )
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "total": total,
        "subtasks": subtasks,
        "result_summary": result_summary,
    }
