import asyncio
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Any
import uuid

from media_tools.api.schemas import (
    PipelineRequest,
    BatchPipelineRequest,
    DownloadBatchRequest,
    CreatorDownloadRequest,
    FullSyncRequest,
    LocalTranscribeRequest,
    CreatorTranscribeRequest,
    ScanDirectoryRequest,
    RecoverAwemeTranscribeRequest,
)
from media_tools.workers.task_dispatcher import _start_task_worker, _create_task, _retry_task_worker
from media_tools.douyin.core.cancel_registry import set_cancel_event, clear_cancel_event
from media_tools.db.core import get_db_connection
from media_tools.repositories.task_repository import TaskRepository
from media_tools.core.config import get_runtime_setting_bool

# WebSocket
from media_tools.api.websocket_manager import websocket_endpoint

# Task operations
from media_tools.services.task_ops import (
    cleanup_stale_tasks,
    _mark_task_cancelled,
)
from media_tools.services.task_state import (
    _active_tasks,
    _register_background_task,
)
from media_tools.services.local_asset_service import _register_local_assets
from media_tools.services.transcript_reconciler import reconcile_transcripts
from media_tools.services.file_browser import select_folder, scan_directory

# Workers
from media_tools.workers.pipeline_worker import (
    _background_pipeline_worker,
    _background_batch_worker,
    _background_download_worker,
)
from media_tools.workers.full_sync_worker import _background_full_sync_worker
from media_tools.workers.local_transcribe_worker import _background_local_transcribe_worker

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)
STALE_TASK_HOURS = 2


def _get_global_setting_bool(key: str, default: bool = False) -> bool:
    """从数据库 SystemSettings 表读取布尔配置（前端设置页面的值）。"""
    return get_runtime_setting_bool(key, default)


router.websocket("/ws")(websocket_endpoint)


@router.post("/pipeline")
async def trigger_pipeline(req: PipelineRequest):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "pipeline", {"url": req.url, "max_counts": req.max_counts, "auto_delete": req.auto_delete})
    _register_background_task(task_id, _background_pipeline_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}


@router.get("/active")
def get_active_tasks():
    try:
        return TaskRepository.find_active()
    except sqlite3.Error:
        logger.exception("get_active_tasks failed")
        raise HTTPException(status_code=500, detail="获取活跃任务失败")


@router.get("/history")
def get_task_history():
    try:
        return TaskRepository.list_recent(50)
    except sqlite3.Error:
        logger.exception("get_task_history failed")
        raise HTTPException(status_code=500, detail="获取任务历史失败")


@router.delete("/history")
def clear_task_history():
    try:
        with get_db_connection() as conn:
            cleanup_stale_tasks(conn)
        TaskRepository.clear_all_history()
        return {"status": "success", "message": "历史任务已清除"}
    except (sqlite3.Error, OSError) as e:
        logger.exception("clear_task_history failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    try:
        active_task = _active_tasks.pop(task_id, None)
        if active_task is not None:
            set_cancel_event(task_id)
            try:
                from media_tools.bilibili.core.downloader import cancel_download
                cancel_download(task_id)
            except (RuntimeError, OSError, ImportError):
                pass
            active_task.cancel()
            try:
                await active_task
            except asyncio.CancelledError:
                pass

        clear_cancel_event(task_id)
        TaskRepository.delete(task_id)
        return {"status": "success", "message": "任务已删除"}
    except (sqlite3.Error, OSError) as e:
        logger.exception(f"delete_task failed for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}")
def get_task_status(task_id: str):
    try:
        task = TaskRepository.find_by_id(task_id)
        if task:
            return task
        raise HTTPException(status_code=404, detail="任务不存在")
    except sqlite3.Error:
        logger.exception("get_task_status failed")
        raise HTTPException(status_code=500, detail="获取任务状态失败")


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    try:
        status, task_type = TaskRepository.get_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            raise HTTPException(status_code=409, detail=f"任务已处于 {status} 状态，无法取消")

        try:
            from media_tools.bilibili.core.downloader import cancel_download
            cancel_download(task_id)
        except (RuntimeError, OSError, ImportError):
            pass

        set_cancel_event(task_id)

        active_task = _active_tasks.pop(task_id, None)
        if active_task is not None:
            active_task.cancel()
            await _mark_task_cancelled(task_id, task_type)
            return {"status": "success", "message": "Task cancelled"}
        else:
            await _mark_task_cancelled(task_id, task_type)
            return {"status": "success", "message": "Task marked as cancelled (was not running)"}
    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError, asyncio.CancelledError) as e:
        logger.exception(f"cancel_task failed for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/auto-retry")
async def set_auto_retry(task_id: str, enabled: bool = True):
    try:
        TaskRepository.set_auto_retry(task_id, enabled)
        return {"status": "success", "message": f"自动重试已{'启用' if enabled else '禁用'}"}
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.exception(f"set_auto_retry failed for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    raise HTTPException(status_code=501, detail="暂停/恢复功能已下线")


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    raise HTTPException(status_code=501, detail="暂停/恢复功能已下线")


@router.post("/{task_id}/rerun")
async def rerun_task(task_id: str):
    try:
        task_type, payload_str, current_status = TaskRepository.get_task_type_payload_status(task_id)
        if not task_type:
            raise HTTPException(status_code=404, detail="任务不存在")

        if current_status not in ("FAILED", "CANCELLED", "PAUSED"):
            raise HTTPException(status_code=409, detail=f"当前状态 {current_status} 不能重新运行")

        try:
            original_params = json.loads(payload_str) if payload_str else {}
        except (json.JSONDecodeError, TypeError):
            original_params = {}
        original_params.pop("msg", None)
        original_params.pop("result_summary", None)
        original_params.pop("subtasks", None)
        original_params["_resumed"] = True

        TaskRepository.mark_running(task_id, 0.0)
        return await _start_task_worker(task_id, task_type, original_params)

    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError, asyncio.CancelledError) as e:
        logger.exception(f"rerun_task failed for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/retry")
async def retry_task(task_id: str):
    try:
        task_type, payload_str = TaskRepository.get_task_type_and_payload(task_id)
        if not task_type:
            raise HTTPException(status_code=404, detail="任务不存在")

        try:
            original_params = json.loads(payload_str) if payload_str else {}
        except (json.JSONDecodeError, TypeError):
            original_params = {}

        return await _retry_task_worker(task_id, task_type, original_params)

    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError, asyncio.CancelledError) as e:
        logger.exception(f"retry_task failed for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/batch")
async def trigger_batch_pipeline(req: BatchPipelineRequest):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "pipeline", {"video_urls": req.video_urls, "auto_delete": req.auto_delete})
    _register_background_task(task_id, _background_batch_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}


@router.post("/download/batch")
async def trigger_download_batch(req: DownloadBatchRequest):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "download", {"video_urls": req.video_urls})
    _register_background_task(task_id, _background_download_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}


@router.post("/download/creator")
async def trigger_creator_download(req: CreatorDownloadRequest):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, f"creator_sync_{req.mode}", {"uid": req.uid, "mode": req.mode, "batch_size": req.batch_size})
    from media_tools.workers.creator_sync import background_creator_download_worker
    _register_background_task(task_id, background_creator_download_worker(task_id, req.uid, req.mode, req.batch_size, {}))
    return {"task_id": task_id, "status": "started"}


@router.post("/download/full-sync")
async def trigger_full_sync(req: FullSyncRequest):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, f"full_sync_{req.mode}", {"mode": req.mode, "batch_size": req.batch_size})
    _register_background_task(task_id, _background_full_sync_worker(task_id, req.mode, req.batch_size, {}))
    return {"task_id": task_id, "status": "started"}


@router.post("/transcribe/local")
async def trigger_local_transcribe(req: LocalTranscribeRequest):
    task_id = str(uuid.uuid4())
    _register_local_assets(req.file_paths, req.delete_after, req.directory_root)
    await _create_task(
        task_id,
        "local_transcribe",
        {"file_paths": req.file_paths, "delete_after": req.delete_after, "directory_root": req.directory_root},
    )
    _register_background_task(task_id, _background_local_transcribe_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}


@router.post("/transcribe/creator")
async def trigger_creator_transcribe(req: CreatorTranscribeRequest):
    task_id = str(uuid.uuid4())
    await _create_task(
        task_id,
        "local_transcribe",
        {"file_paths": [], "delete_after": False, "directory_root": None, "creator_uid": req.uid},
    )
    from media_tools.workers.creator_transcribe_worker import background_creator_transcribe_worker
    _register_background_task(task_id, background_creator_transcribe_worker(task_id, req.uid))
    file_count = 0
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """SELECT COUNT(1)
                   FROM media_assets
                   WHERE creator_uid = ?
                     AND video_status IN ('downloaded', 'pending')
                     AND transcript_status IN ('pending', 'none', 'failed')""",
                (req.uid,),
            )
            row = cursor.fetchone()
            if row:
                file_count = int(row[0] or 0)
    except (sqlite3.Error, OSError, ValueError):
        file_count = 0

    return {"task_id": task_id, "status": "started", "file_count": file_count}


@router.post("/recover/aweme")
async def trigger_recover_aweme_transcribe(req: RecoverAwemeTranscribeRequest):
    task_id = str(uuid.uuid4())
    await _create_task(
        task_id,
        "recover_aweme_transcribe",
        {"creator_uid": req.creator_uid, "aweme_id": req.aweme_id, "title": req.title},
    )
    from media_tools.workers.aweme_recover_worker import recover_aweme_transcribe

    _register_background_task(task_id, recover_aweme_transcribe(task_id, req.creator_uid, req.aweme_id, req.title))
    return {"task_id": task_id, "status": "started"}


@router.post("/transcribe/select-folder")
def _select_folder():
    return select_folder()


@router.post("/transcribe/scan")
def _scan_directory(req: ScanDirectoryRequest):
    return scan_directory(req.directory)


@router.post("/reconcile-transcripts")
def _reconcile_transcripts():
    return reconcile_transcripts()
