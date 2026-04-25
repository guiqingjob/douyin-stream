import asyncio
import logging
from typing import Any
from media_tools.pipeline.worker import run_local_transcribe
from media_tools.services.task_ops import update_task_progress, _complete_task, _fail_task
from media_tools.services.task_state import _task_heartbeat

logger = logging.getLogger(__name__)


async def _background_local_transcribe_worker(task_id: str, req: Any):
    async def _progress_fn(p, m, stage=""):
        await update_task_progress(task_id, p, m, "local_transcribe", stage=stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        result = await run_local_transcribe(
            req.file_paths,
            _progress_fn,
            req.delete_after,
        )
        s_count = result.get("success_count", 0)
        f_count = result.get("failed_count", 0)
        total = result.get("total", 0)
        msg = "没有找到有效的音视频文件" if total == 0 else f"本地转写完成：成功 {s_count} 个，失败 {f_count} 个"
        await _complete_task(task_id, "local_transcribe", msg)
    except (RuntimeError, OSError) as e:
        logger.error(f"Local transcribe worker failed: {e}")
        await _fail_task(task_id, "local_transcribe", str(e))
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
