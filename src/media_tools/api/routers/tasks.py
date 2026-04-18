import asyncio
import sqlite3
import json
import logging
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Any, List
import uuid
from pathlib import Path
import sys
import os
from media_tools.pipeline.worker import run_pipeline_for_user, run_batch_pipeline, run_download_only
from media_tools.pipeline.media_extensions import MEDIA_EXTENSIONS
from media_tools.douyin.core.config_mgr import get_config
from media_tools.db.core import get_db_connection

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)
STALE_TASK_HOURS = 2
LOCAL_CREATOR_UID = "local:upload"
LOCAL_CREATOR_NAME = "本地上传"


def _is_allowed_scan_path(dir_path: Path) -> bool:
    """Restrict directory scanning to safe roots."""
    resolved = dir_path.resolve()
    dir_str = str(resolved)

    # Block traversal attempts explicitly
    if ".." in str(dir_path):
        return False

    home = Path.home().resolve()
    downloads = get_config().get_download_path().resolve()
    allowed_roots = [home, downloads, Path("/tmp").resolve()]
    if sys.platform == "darwin":
        allowed_roots.append(Path("/Volumes").resolve())

    for root in allowed_roots:
        root_str = str(root)
        if dir_str.startswith(root_str + os.sep) or dir_str == root_str:
            return True
    return False

class PipelineRequest(BaseModel):
    url: str
    max_counts: int = 5
    auto_delete: bool = True


def cleanup_stale_tasks(conn: sqlite3.Connection):
    # Mark stale PENDING/RUNNING tasks as FAILED
    cutoff = (datetime.now() - timedelta(hours=STALE_TASK_HOURS)).isoformat()
    conn.execute(
        """
        UPDATE task_queue
        SET
            status = 'FAILED',
            progress = 0.0,
            error_msg = CASE
                WHEN error_msg IS NULL OR error_msg = '' THEN '任务长时间没有更新，已自动标记为失败，请重新发起。'
                ELSE error_msg
            END,
            update_time = ?
        WHERE status IN ('PENDING', 'RUNNING')
          AND update_time IS NOT NULL
          AND update_time < ?
        """,
        (datetime.now().isoformat(), cutoff),
    )

    # Delete old completed tasks (older than 7 days)
    delete_cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    conn.execute(
        "DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED') AND update_time < ?",
        (delete_cutoff,),
    )
    conn.commit()

# --- WebSocket for task monitoring ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# --- Active-task registry -----------------------------------------------------
# Tracks the asyncio.Task handle for every background worker currently running,
# keyed by task_id. Populated by _register_background_task, auto-evicted by
# add_done_callback. Enables POST /tasks/{id}/cancel to actually interrupt work.
_active_tasks: dict[str, "asyncio.Task[Any]"] = {}  # type: ignore[type-arg]


def _register_background_task(task_id: str, coro) -> "asyncio.Task[Any]":  # type: ignore[type-arg]
    task = asyncio.create_task(coro)
    _active_tasks[task_id] = task

    def _on_done(t: "asyncio.Task[Any]") -> None:  # type: ignore[type-arg]
        _active_tasks.pop(task_id, None)
        # Surface unexpected crashes in the log; CancelledError is normal.
        if not t.cancelled():
            exc = t.exception()
            if exc is not None:
                logger.error(f"Background task {task_id} crashed: {exc!r}")

    task.add_done_callback(_on_done)
    return task


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async def _heartbeat():
        """Send ping every 20 seconds to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(20)
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _pong_handler():
        """Handle incoming pong responses and detect stale connections."""
        try:
            while True:
                data = await websocket.receive_text()
                # Acknowledge but don't crash on any message
                if data:
                    # Could log or handle pong here if needed
                    pass
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    heartbeat_task = asyncio.create_task(_heartbeat())
    try:
        while True:
            # Just keep connection alive, we broadcast updates from the worker
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

async def notify_task_update(task_id: str, progress: float, msg: str, status: str = "RUNNING", task_type: str = "pipeline"):
    await manager.broadcast({
        "task_id": task_id,
        "progress": progress,
        "msg": msg,
        "status": status,
        "task_type": task_type
    })

def _merge_task_payload(existing_payload: str | None, msg: str) -> str:
    base_payload: dict = {}
    if existing_payload:
        try:
            parsed = json.loads(existing_payload)
            if isinstance(parsed, dict):
                base_payload = parsed
        except Exception:
            base_payload = {}
    base_payload["msg"] = msg
    return json.dumps(base_payload, ensure_ascii=False)

def _merge_payload_from_db(conn: sqlite3.Connection, task_id: str, msg: str) -> str:
    try:
        cursor = conn.execute("SELECT payload FROM task_queue WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        existing = row["payload"] if row else None
    except Exception:
        existing = None
    return _merge_task_payload(existing, msg)

def _local_asset_id(file_path: str) -> str:
    resolved = str(Path(file_path).resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:24]
    return f"local:{digest}"

def _compute_folder_path(file_path: Path, directory_root: str | None) -> str:
    if not directory_root:
        return ""
    try:
        root = Path(directory_root).resolve()
        p = file_path.resolve()
        rel = p.parent.relative_to(root)
        rel_str = rel.as_posix()
        return "" if rel_str == "." else rel_str
    except Exception:
        return "(其他)"

def _register_local_assets(file_paths: list[str], delete_after: bool, directory_root: str | None = None) -> None:
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            INSERT OR IGNORE INTO creators (uid, sec_user_id, nickname, platform, sync_status, last_fetch_time)
            VALUES (?, ?, ?, ?, 'active', ?)
            """,
            (LOCAL_CREATOR_UID, "", LOCAL_CREATOR_NAME, "local", now),
        )
        for raw_path in file_paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            asset_id = _local_asset_id(str(path))
            folder_path = _compute_folder_path(path, directory_root)
            conn.execute(
                """
                INSERT OR IGNORE INTO media_assets
                (asset_id, creator_uid, source_url, title, video_status, transcript_status, folder_path, create_time, update_time)
                VALUES (?, ?, ?, ?, 'downloaded', 'pending', ?, ?, ?)
                """,
                (asset_id, LOCAL_CREATOR_UID, str(path.resolve()), path.stem, folder_path, now, now),
            )
        conn.commit()

async def update_task_progress(task_id: str, progress: float, msg: str, task_type: str = "pipeline"):
    try:
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute(
                """INSERT INTO task_queue (task_id, task_type, status, progress, payload, create_time, update_time)
                   VALUES (?, ?, 'RUNNING', ?, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                       status = 'RUNNING',
                       progress = excluded.progress,
                       payload = excluded.payload,
                       update_time = excluded.update_time""",
                (task_id, task_type, progress, payload_str, now, now)
            )
        await notify_task_update(task_id, progress, msg, "RUNNING", task_type)
    except Exception as e:
        logger.error(f"Error updating task: {e}")


async def _mark_task_cancelled(task_id: str, task_type: str) -> None:
    """Called from a worker's asyncio.CancelledError handler.

    Writes CANCELLED status + message, broadcasts WS. Idempotent: if the row
    is already terminal (COMPLETED/FAILED/CANCELLED) we don't overwrite.
    """
    msg = "任务已取消"
    try:
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute(
                """UPDATE task_queue
                   SET status='CANCELLED', payload=?, update_time=CURRENT_TIMESTAMP
                   WHERE task_id=? AND status IN ('PENDING', 'RUNNING')""",
                (payload_str, task_id),
            )
        await notify_task_update(task_id, 0.0, msg, "CANCELLED", task_type)
    except Exception as e:
        logger.error(f"Failed to mark task {task_id} as cancelled: {e}")

async def _background_pipeline_worker(task_id: str, req: PipelineRequest):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, "pipeline")
        
    try:
        result = await run_pipeline_for_user(
            url=req.url, 
            max_counts=req.max_counts, 
            update_progress_fn=_progress_fn,
            delete_after=req.auto_delete
        )
        msg = "成功转写完成"
        error_msg = None
        status = "COMPLETED"
        if result:
            s_count = result.get("success_count", 0)
            f_count = result.get("failed_count", 0)
            failed_items = result.get("failed_items", []) or []
            if s_count == 0 and f_count == 0:
                msg = "未找到新视频或链接无效"
            elif s_count == 0 and f_count > 0:
                status = "FAILED"
                first_error = failed_items[0]["error"] if failed_items else "全部视频转写失败"
                msg = f"全部转写失败：共 {f_count} 个"
                error_msg = first_error
            else:
                msg = f"成功转写 {s_count} 个视频，失败 {f_count} 个"

        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute(
                "UPDATE task_queue SET status=?, progress=1.0, payload=?, error_msg=? WHERE task_id=?",
                (status, payload_str, error_msg, task_id)
            )
        await notify_task_update(task_id, 1.0, msg, status, "pipeline")
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", "pipeline")

async def _create_task(task_id: str, task_type: str, request_params: dict):
    """Create a task with original request parameters stored in payload for retry."""
    payload_str = json.dumps({**request_params, "msg": "Initializing..."}, ensure_ascii=False)
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO task_queue (task_id, task_type, status, progress, payload, create_time, update_time) VALUES (?, ?, 'RUNNING', 0.0, ?, ?, ?)",
            (task_id, task_type, payload_str, now, now)
        )
    await notify_task_update(task_id, 0.0, "Initializing...", "RUNNING", task_type)


@router.post("/pipeline")
async def trigger_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "pipeline", {"url": req.url, "max_counts": req.max_counts})
    _register_background_task(task_id, _background_pipeline_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}

@router.get("/active")
def get_active_tasks():
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM task_queue WHERE status IN ('PENDING', 'RUNNING')")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        logger.exception("get_active_tasks failed")
        return []

@router.get("/history")
def get_task_history():
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM task_queue ORDER BY update_time DESC LIMIT 50")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        logger.exception("get_task_history failed")
        return []

@router.get("/{task_id}")
def get_task_status(task_id: str):
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"status": "NOT_FOUND"}
    except Exception:
        logger.exception("get_task_status failed")
        return {"status": "ERROR"}

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running or pending task."""
    try:
        # Check task exists and is cancellable
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT status, task_type FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "message": "Task not found"}
            if row["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                return {"status": "error", "message": f"Task already {row['status']}"}
            task_type = row["task_type"]

        # Cancel the asyncio task if running
        if task_id in _active_tasks:
            _active_tasks[task_id].cancel()
            await _mark_task_cancelled(task_id, task_type)
            return {"status": "success", "message": "Task cancelled"}
        else:
            # Task not in active registry, just mark as cancelled
            await _mark_task_cancelled(task_id, task_type)
            return {"status": "success", "message": "Task marked as cancelled (was not running)"}
    except Exception as e:
        logger.exception(f"cancel_task failed for {task_id}")
        return {"status": "error", "message": str(e)}

@router.post("/{task_id}/retry")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    """Retry a failed task using original parameters from payload."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT task_type, payload FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "message": "Task not found"}

            task_type = row["task_type"]
            payload_str = row["payload"]

        # Parse original parameters from payload
        try:
            original_params = json.loads(payload_str) if payload_str else {}
        except Exception:
            original_params = {}

        # Remove internal fields
        original_params.pop("msg", None)

        # Determine task type and create new task
        if task_type == "pipeline" and "url" in original_params:
            req = PipelineRequest(
                url=original_params.get("url", ""),
                max_counts=original_params.get("max_counts", 5),
                auto_delete=original_params.get("auto_delete", True)
            )
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, task_type, {"url": req.url, "max_counts": req.max_counts})
            _register_background_task(new_task_id, _background_pipeline_worker(new_task_id, req))
            return {"task_id": new_task_id, "status": "started", "message": "Pipeline task retry started"}

        elif task_type == "pipeline" and "video_urls" in original_params:
            req = BatchPipelineRequest(
                video_urls=original_params.get("video_urls", []),
                auto_delete=original_params.get("auto_delete", True)
            )
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, task_type, {"video_urls": req.video_urls})
            _register_background_task(new_task_id, _background_batch_worker(new_task_id, req))
            return {"task_id": new_task_id, "status": "started", "message": "Batch pipeline task retry started"}

        elif task_type == "download" and "video_urls" in original_params:
            req = DownloadBatchRequest(video_urls=original_params.get("video_urls", []))
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, task_type, {"video_urls": req.video_urls})
            _register_background_task(new_task_id, _background_download_worker(new_task_id, req))
            return {"task_id": new_task_id, "status": "started", "message": "Download task retry started"}

        elif task_type.startswith("creator_sync") and "uid" in original_params:
            uid = original_params.get("uid")
            mode = original_params.get("mode", "incremental")
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, f"creator_sync_{mode}", {"uid": uid, "mode": mode})
            _register_background_task(new_task_id, _background_creator_download_worker(new_task_id, uid, mode))
            return {"task_id": new_task_id, "status": "started", "message": "Creator download task retry started"}

        elif task_type.startswith("full_sync") and "mode" in original_params:
            mode = original_params.get("mode", "incremental")
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, f"full_sync_{mode}", {"mode": mode})
            _register_background_task(new_task_id, _background_full_sync_worker(new_task_id, mode))
            return {"task_id": new_task_id, "status": "started", "message": "Full sync task retry started"}

        elif task_type == "local_transcribe" and "file_paths" in original_params:
            req = LocalTranscribeRequest(
                file_paths=original_params.get("file_paths", []),
                delete_after=original_params.get("delete_after", False),
                directory_root=original_params.get("directory_root")
            )
            _register_local_assets(req.file_paths, req.delete_after, req.directory_root)
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, task_type, {"file_paths": req.file_paths, "delete_after": req.delete_after})
            _register_background_task(new_task_id, _background_local_transcribe_worker(new_task_id, req))
            return {"task_id": new_task_id, "status": "started", "message": "Local transcribe task retry started"}

        else:
            return {"status": "error", "message": f"Unsupported task type for retry: {task_type}"}

    except Exception as e:
        logger.exception(f"retry_task failed for {task_id}")
        return {"status": "error", "message": str(e)}

class BatchPipelineRequest(BaseModel):
    video_urls: List[str]
    auto_delete: bool = True

class DownloadBatchRequest(BaseModel):
    video_urls: List[str]

class CreatorDownloadRequest(BaseModel):
    uid: str
    mode: str = "incremental"

class FullSyncRequest(BaseModel):
    mode: str = "incremental"

async def _background_batch_worker(task_id: str, req: BatchPipelineRequest):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, "pipeline")

    try:
        result = await run_batch_pipeline(
            video_urls=req.video_urls,
            update_progress_fn=_progress_fn,
            delete_after=req.auto_delete
        )
        success_count = result.get('success_count', 0)
        failed_count = result.get('failed_count', 0)
        failed_items = result.get('failed_items', []) or []
        status = "COMPLETED"
        error_msg = None
        if success_count == 0 and failed_count > 0:
            status = "FAILED"
            error_msg = failed_items[0]["error"] if failed_items else "全部视频处理失败"
        msg = f"批量处理完成：成功 {success_count} 个，失败 {failed_count} 个"
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute(
                "UPDATE task_queue SET status=?, progress=1.0, payload=?, error_msg=? WHERE task_id=?",
                (status, payload_str, error_msg, task_id)
            )
        await notify_task_update(task_id, 1.0, msg, status, "pipeline")
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", "pipeline")

@router.post("/pipeline/batch")
async def trigger_batch_pipeline(req: BatchPipelineRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "pipeline", {"video_urls": req.video_urls})
    _register_background_task(task_id, _background_batch_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}

async def _background_download_worker(task_id: str, req: DownloadBatchRequest):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, "download")

    try:
        result = await run_download_only(
            video_urls=req.video_urls,
            update_progress_fn=_progress_fn,
        )
        msg = f"下载完成：成功 {result.get('success_count', 0)} 个，失败 {result.get('failed_count', 0)} 个"
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (payload_str, task_id))
        await notify_task_update(task_id, 1.0, msg, "COMPLETED", "download")
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", "download")

@router.post("/download/batch")
async def trigger_download_batch(req: DownloadBatchRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "download", {"video_urls": req.video_urls})
    _register_background_task(task_id, _background_download_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}

async def _background_creator_download_worker(task_id: str, uid: str, mode: str = "incremental"):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, f"creator_sync_{mode}")

    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT uid, sec_user_id, nickname, platform FROM creators WHERE uid = ? LIMIT 1",
                (uid,),
            )
            creator_row = cursor.fetchone()

        if not creator_row:
            raise RuntimeError(f"Creator not found: {uid}")

        platform = (creator_row.get("platform") if isinstance(creator_row, dict) else creator_row["platform"]) or "douyin"
        sec_user_id = (creator_row.get("sec_user_id") if isinstance(creator_row, dict) else creator_row["sec_user_id"]) or ""
        display_name = (creator_row.get("nickname") if isinstance(creator_row, dict) else creator_row["nickname"]) or uid

        await _progress_fn(0.05, f"开始同步 {display_name} 的视频（{mode}）...")

        skip_existing = mode != "full"

        if platform == "bilibili":
            from media_tools.bilibili.core.downloader import download_up_by_url
            from media_tools.douyin.core.config_mgr import get_config

            mid = sec_user_id or uid.split(":", 1)[-1]
            url = f"https://space.bilibili.com/{mid}"
            result = await asyncio.to_thread(download_up_by_url, url, None, skip_existing)

            new_files = (result.get("new_files") or []) if isinstance(result, dict) else []
            config = get_config()
            if config.is_auto_transcribe() and new_files:
                from media_tools.pipeline.config import load_pipeline_config
                from media_tools.pipeline.orchestrator_v2 import create_orchestrator

                await _progress_fn(0.7, f"下载完成，准备转写 {len(new_files)} 个视频...")
                pipeline_config = load_pipeline_config()
                orchestrator = create_orchestrator(pipeline_config, creator_folder_override=display_name)
                delete_after = config.is_auto_delete_video()
                total = len(new_files)
                for index, file_path in enumerate(new_files, 1):
                    await _progress_fn(0.7 + 0.3 * ((index - 1) / total), f"正在转写 ({index}/{total})")
                    await orchestrator.transcribe_with_retry(Path(file_path))
                    if delete_after:
                        try:
                            Path(file_path).unlink(missing_ok=True)
                        except Exception:
                            pass
        else:
            from media_tools.douyin.core.downloader import download_by_url

            if sec_user_id.startswith("MS4w"):
                url = f"https://www.douyin.com/user/{sec_user_id}"
            else:
                url = f"https://www.douyin.com/user/{uid}"

            result = await asyncio.to_thread(download_by_url, url, None, False, skip_existing)

        if not isinstance(result, dict) or not result.get("success"):
            raise RuntimeError(f"下载失败: {display_name}")

        new_count = len(result.get("new_files", []) or [])

        # 更新 B站创作者昵称
        if platform == "bilibili":
            uploader = result.get("uploader")
            if uploader and uploader.get("nickname"):
                with get_db_connection() as conn:
                    conn.execute(
                        "UPDATE creators SET nickname = ?, homepage_url = ? WHERE uid = ?",
                        (uploader["nickname"], uploader.get("homepage_url", ""), uid),
                    )
                    conn.commit()

        msg = f"{display_name} 同步完成：{new_count} 个新视频（{mode}）"
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (payload_str, task_id))
        await notify_task_update(task_id, 1.0, msg, "COMPLETED", f"creator_sync_{mode}")
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", f"creator_sync_{mode}")

@router.post("/download/creator")
async def trigger_creator_download(req: CreatorDownloadRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, f"creator_sync_{req.mode}", {"uid": req.uid, "mode": req.mode})
    _register_background_task(task_id, _background_creator_download_worker(task_id, req.uid, req.mode))
    return {"task_id": task_id, "status": "started"}

async def _background_full_sync_worker(task_id: str, mode: str = "incremental"):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, f"full_sync_{mode}")

    try:
        from media_tools.douyin.core.following_mgr import list_users
        from media_tools.douyin.core.downloader import download_by_uid

        users = list_users()
        if not users:
            msg = "关注列表为空"
            with get_db_connection() as conn:
                payload_str = _merge_payload_from_db(conn, task_id, msg)
                conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (payload_str, task_id))
            await notify_task_update(task_id, 1.0, msg, "COMPLETED", f"full_sync_{mode}")
            return

        total = len(users)
        creator_success = 0
        creator_failed = 0
        new_video_count = 0
        skip_existing = mode != "full"

        for index, user in enumerate(users, 1):
            uid = user.get("uid") or ""
            name = user.get("nickname") or user.get("name") or uid or f"creator-{index}"
            await _progress_fn((index - 1) / total, f"正在同步 {name} ({index}/{total}) [{mode}]")
            try:
                result = await asyncio.to_thread(download_by_uid, uid, None, skip_existing)
                if isinstance(result, dict) and result.get("success"):
                    creator_success += 1
                    new_video_count += len(result.get("new_files") or [])
                else:
                    creator_failed += 1
            except Exception as exc:
                creator_failed += 1
                await update_task_progress(task_id, (index - 1) / total, f"{name} 同步失败: {exc}", f"full_sync_{mode}")
            finally:
                await update_task_progress(task_id, index / total, f"已完成 {name} ({index}/{total})", f"full_sync_{mode}")

        msg = f"全量同步完成：成功 {creator_success} 位，失败 {creator_failed} 位，新增 {new_video_count} 个视频（{mode}）"
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (payload_str, task_id))
        await notify_task_update(task_id, 1.0, msg, "COMPLETED", f"full_sync_{mode}")
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", f"full_sync_{mode}")

@router.post("/download/full-sync")
async def trigger_full_sync(req: FullSyncRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, f"full_sync_{req.mode}", {"mode": req.mode})
    _register_background_task(task_id, _background_full_sync_worker(task_id, req.mode))
    return {"task_id": task_id, "status": "started"}


# --- Local transcribe ---

class LocalTranscribeRequest(BaseModel):
    file_paths: List[str]
    delete_after: bool = False
    directory_root: str | None = None

class ScanDirectoryRequest(BaseModel):
    directory: str

async def _background_local_transcribe_worker(task_id: str, req: LocalTranscribeRequest):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, "local_transcribe")

    try:
        from media_tools.pipeline.worker import run_local_transcribe
        result = await run_local_transcribe(
            req.file_paths,
            _progress_fn,
            req.delete_after,
        )
        s_count = result.get("success_count", 0)
        f_count = result.get("failed_count", 0)
        total = result.get("total", 0)
        msg = "没有找到有效的音视频文件" if total == 0 else f"本地转写完成：成功 {s_count} 个，失败 {f_count} 个"
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (payload_str, task_id))
        await notify_task_update(task_id, 1.0, msg, "COMPLETED", "local_transcribe")
    except Exception as e:
        logger.error(f"Local transcribe worker failed: {e}")
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", "local_transcribe")

@router.post("/transcribe/local")
async def trigger_local_transcribe(req: LocalTranscribeRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    _register_local_assets(req.file_paths, req.delete_after, req.directory_root)
    await _create_task(task_id, "local_transcribe", {"file_paths": req.file_paths, "delete_after": req.delete_after})
    _register_background_task(task_id, _background_local_transcribe_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}

@router.post("/transcribe/scan")
def scan_directory(req: ScanDirectoryRequest):
    dir_path = Path(req.directory)
    if not _is_allowed_scan_path(dir_path):
        raise HTTPException(status_code=400, detail="Invalid directory path")
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="目录不存在")
    extensions = MEDIA_EXTENSIONS
    files = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            files.append({"path": str(f), "name": f.name, "size_mb": round(f.stat().st_size / 1024 / 1024, 1)})
    return {"directory": str(dir_path), "files": files}
