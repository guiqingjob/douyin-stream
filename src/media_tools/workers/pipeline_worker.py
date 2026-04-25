import asyncio
from typing import Any
from media_tools.pipeline.worker import run_pipeline_for_user, run_batch_pipeline, run_download_only
from media_tools.services.task_ops import update_task_progress, _complete_task, _fail_task
from media_tools.services.task_state import _task_heartbeat


async def _background_pipeline_worker(task_id: str, req: Any):
    async def _progress_fn(p, m, stage=""):
        await update_task_progress(task_id, p, m, "pipeline", stage=stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        result = await run_pipeline_for_user(
            url=req.url,
            max_counts=req.max_counts,
            update_progress_fn=_progress_fn,
            delete_after=req.auto_delete,
            task_id=task_id,
        )
        msg = "成功转写完成"
        error_msg = None
        status = "COMPLETED"

        s_count = result.get("success_count", 0)
        f_count = result.get("failed_count", 0)
        total = result.get("total", s_count + f_count)
        subtasks = result.get("subtasks", [])

        result_summary = {
            "success": s_count,
            "failed": f_count,
            "skipped": 0,
            "total": total,
        }

        if s_count == 0 and f_count == 0:
            msg = "未找到新视频或链接无效"
        elif s_count == 0 and f_count > 0:
            status = "FAILED"
            first_error = subtasks[0].get("error") if subtasks else "全部视频转写失败"
            msg = f"全部转写失败：共 {f_count} 个"
            error_msg = first_error
        else:
            msg = f"成功转写 {s_count} 个视频，失败 {f_count} 个"

        from media_tools.services.task_ops import _merge_payload_from_db
        from media_tools.db.core import get_db_connection
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, subtasks)
            conn.execute(
                "UPDATE task_queue SET status=?, progress=1.0, payload=?, error_msg=? WHERE task_id=?",
                (status, payload_str, error_msg, task_id)
            )
        from media_tools.services.task_ops import notify_task_update
        await notify_task_update(task_id, 1.0, msg, status, "pipeline", result_summary, subtasks)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        from media_tools.db.core import get_db_connection
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        from media_tools.services.task_ops import notify_task_update
        await notify_task_update(task_id, 0.0, str(e), "FAILED", "pipeline")
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass


async def _background_batch_worker(task_id: str, req: Any):
    async def _progress_fn(p, m, stage=""):
        await update_task_progress(task_id, p, m, "pipeline", stage=stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        result = await run_batch_pipeline(
            video_urls=req.video_urls,
            update_progress_fn=_progress_fn,
            delete_after=req.auto_delete,
            task_id=task_id,
        )
        success_count = result.get('success_count', 0)
        failed_count = result.get('failed_count', 0)
        failed_items = result.get('failed_items', []) or []
        if success_count == 0 and failed_count > 0:
            await _fail_task(task_id, "pipeline", failed_items[0]["error"] if failed_items else "全部视频处理失败")
        else:
            await _complete_task(task_id, "pipeline", f"批量处理完成：成功 {success_count} 个，失败 {failed_count} 个")
    except (RuntimeError, OSError) as e:
        await _fail_task(task_id, "pipeline", str(e))
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass


async def _background_download_worker(task_id: str, req: Any):
    async def _progress_fn(p, m, stage=""):
        await update_task_progress(task_id, p, m, "download", stage=stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        result = await run_download_only(
            video_urls=req.video_urls,
            update_progress_fn=_progress_fn,
            task_id=task_id,
        )
        await _complete_task(
            task_id, "download",
            f"下载完成：成功 {result.get('success_count', 0)} 个，失败 {result.get('failed_count', 0)} 个"
        )
    except (RuntimeError, OSError) as e:
        await _fail_task(task_id, "download", str(e))
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
