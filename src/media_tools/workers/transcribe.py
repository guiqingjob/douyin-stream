"""转写工作者 - 视频转写逻辑"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def transcribe_files(task_id: str, _progress_fn, new_files: list, display_name: str, auto_delete: bool = False):
    """转写一批视频文件，返回统计信息。"""
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    await _progress_fn(0.6, f"下载完成，准备转写 {len(new_files)} 个视频...", stage="transcribing")
    pipeline_config = load_pipeline_config()
    orchestrator = create_orchestrator(pipeline_config, creator_folder_override=display_name)
    delete_after = auto_delete
    total = len(new_files)
    success_count = 0
    failed_count = 0
    subtasks: list[dict] = []

    for index, file_path in enumerate(new_files, 1):
        title = Path(file_path).stem[:60]
        await _progress_fn(
            0.6 + 0.3 * ((index - 1) / total),
            f"正在转写 ({index}/{total})",
            subtasks=subtasks,
            stage="transcribing",
        )
        transcribe_ok = False
        error_msg = ""
        try:
            result = await orchestrator.transcribe_with_retry(Path(file_path))
            transcribe_ok = bool(getattr(result, "success", False))
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"转写失败 {file_path}: {e}")

        if transcribe_ok:
            success_count += 1
            subtasks.append({"title": title, "status": "completed"})
        else:
            failed_count += 1
            subtasks.append({"title": title, "status": "failed", "error": error_msg or "转写失败"})

        if delete_after and transcribe_ok:
            try:
                Path(file_path).unlink()
            except FileNotFoundError:
                pass
            except OSError as e:
                logger.error(f"删除转写后视频失败: {file_path}, {e}")

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
