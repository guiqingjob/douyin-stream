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
    try:
        status, task_type = TaskRepository.get_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        if status != "RUNNING":
            raise HTTPException(status_code=409, detail=f"任务未在运行（当前: {status}）")
        raise HTTPException(status_code=409, detail="当前下载器不支持暂停，请使用取消功能")
    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.exception(f"pause_task failed for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    try:
        status, task_type = TaskRepository.get_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        if status != "PAUSED":
            raise HTTPException(status_code=409, detail=f"任务未暂停（当前: {status}）")
        raise HTTPException(status_code=409, detail="当前下载器不支持恢复")
    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.exception(f"resume_task failed for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """对指定博主所有待转写的素材发起转写任务"""
    from media_tools.common.paths import get_download_path
    from media_tools.services.asset_file_ops import _resolve_asset_video_file, get_source_url_column

    download_dir = get_download_path()
    file_paths: list[str] = []
    not_found: list[str] = []

    # 第一步：从 DB 查找待转写素材，解析视频文件路径
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            source_url_select = get_source_url_column(conn)
            cursor = conn.execute(
                f"""SELECT asset_id, creator_uid, {source_url_select} video_path
                    FROM media_assets
                    WHERE creator_uid = ?
                      AND video_status IN ('downloaded', 'pending')
                      AND transcript_status IN ('pending', 'none', 'failed')
                    """,
                (req.uid,),
            )
            for row in cursor.fetchall():
                resolved = _resolve_asset_video_file(
                    creator_uid=row["creator_uid"],
                    source_url=row["source_url"],
                    video_path=row["video_path"],
                    download_dir=download_dir,
                )
                if resolved and resolved.exists():
                    file_paths.append(str(resolved))
                else:
                    # DB 路径与实际文件不一致（文件被移动/重命名），按文件名全盘搜索
                    video_path = row["video_path"] or ""
                    filename = Path(video_path).name if video_path else ""
                    if filename:
                        found = None
                        stem = Path(filename).stem
                        for match in download_dir.rglob(f"{stem}*.mp4"):
                            if match.is_file():
                                found = match
                                break
                        if not found:
                            # 用更宽松的搜索：去掉扩展名，搜索所有视频格式
                            for match in download_dir.rglob(f"{stem}*"):
                                if match.is_file() and match.suffix.lower() in (".mp4", ".webm", ".mkv", ".avi", ".mov"):
                                    found = match
                                    break
                        if found:
                            file_paths.append(str(found))
                            try:
                                new_rel = str(found.relative_to(download_dir))
                                conn.execute(
                                    "UPDATE media_assets SET video_path = ? WHERE asset_id = ?",
                                    (new_rel, row["asset_id"]),
                                )
                            except (ValueError, sqlite3.Error):
                                pass
                        else:
                            not_found.append(filename)
    except (sqlite3.Error, OSError) as e:
        raise HTTPException(status_code=500, detail=f"查询待转写素材失败: {e}")

    # 第二步：扫描下载目录，找到磁盘上存在但 DB 中没有记录或已标记完成的未转写文件
    try:
        # 获取博主的下载子目录
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT DISTINCT folder_path FROM media_assets WHERE creator_uid = ? AND folder_path IS NOT NULL",
                (req.uid,),
            )
            folder_names = [row["folder_path"] for row in cursor.fetchall() if row["folder_path"]]

            # 也查 nickname
            cursor2 = conn.execute("SELECT nickname FROM creators WHERE uid = ?", (req.uid,))
            nickname_row = cursor2.fetchone()
            if nickname_row and nickname_row["nickname"]:
                folder_names.append(nickname_row["nickname"])

        # 收集 DB 中所有已转写完成和已有路径的文件名（stem）
        completed_stems: set[str] = set()
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT video_path FROM media_assets WHERE creator_uid = ? AND video_path IS NOT NULL AND video_path != ''",
                (req.uid,),
            )
            for row in cursor.fetchall():
                vp = row["video_path"] or ""
                if vp:
                    completed_stems.add(Path(vp).stem.rstrip("_0123456789"))

        # 扫描文件夹找未在 DB 中的视频
        for folder_name in folder_names:
            folder = download_dir / folder_name
            if not folder.is_dir():
                continue
            for f in folder.glob("*.mp4"):
                base_stem = f.stem.rstrip("_0123456789")
                if base_stem not in completed_stems:
                    file_paths.append(str(f))
                    # 注册到 DB
                    try:
                        from media_tools.db.core import get_db_connection as _get_conn
                        import uuid as _uuid
                        asset_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, str(f.resolve())))
                        now = datetime.now().isoformat()
                        with _get_conn() as conn:
                            conn.execute(
                                """INSERT OR IGNORE INTO media_assets
                                   (asset_id, creator_uid, title, video_path, video_status, transcript_status, folder_path, create_time, update_time)
                                   VALUES (?, ?, ?, ?, 'downloaded', 'pending', ?, ?, ?)""",
                                (asset_id, req.uid, f.stem, str(f.relative_to(download_dir)), folder_name, now, now),
                            )
                    except (sqlite3.Error, OSError, ValueError):
                        pass
    except (sqlite3.Error, OSError) as e:
        logger.warning(f"扫描下载目录失败: {e}")

    if not file_paths:
        if not_found:
            raise HTTPException(status_code=404, detail=f"该博主有 {len(not_found)} 个待转写素材，但视频文件在磁盘上找不到（可能已被移动或删除）。可在设置中清理缺失素材。")
        raise HTTPException(status_code=404, detail="该博主没有待转写的素材")

    # 标记这些素材的 transcript_status 为 pending（如果之前是 none）
    try:
        with get_db_connection() as conn:
            conn.execute(
                """UPDATE media_assets SET transcript_status = 'pending'
                   WHERE creator_uid = ? AND transcript_status = 'none'
                      AND video_status IN ('downloaded', 'pending')""",
                (req.uid,),
            )
    except sqlite3.Error:
        pass

    task_id = str(uuid.uuid4())
    await _create_task(
        task_id,
        "local_transcribe",
        {"file_paths": file_paths, "delete_after": False, "directory_root": None, "creator_uid": req.uid},
    )

    class _CreatorTranscribeReq:
        file_paths: list[str]
        delete_after: bool = False
        directory_root: str | None = None

    fake_req = _CreatorTranscribeReq()
    fake_req.file_paths = file_paths

    _register_background_task(task_id, _background_local_transcribe_worker(task_id, fake_req))
    return {"task_id": task_id, "status": "started", "file_count": len(file_paths)}


@router.post("/transcribe/select-folder")
def _select_folder():
    return select_folder()


@router.post("/transcribe/scan")
def _scan_directory(req: ScanDirectoryRequest):
    return scan_directory(req.directory)


@router.post("/reconcile-transcripts")
def _reconcile_transcripts():
    return reconcile_transcripts()
