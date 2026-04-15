import asyncio
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
import uuid
from media_tools.pipeline.worker import run_pipeline_for_user, run_batch_pipeline, run_download_only
from media_tools.db.core import get_db_connection

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)
STALE_TASK_HOURS = 2

class PipelineRequest(BaseModel):
    url: str
    max_counts: int = 5
    auto_delete: bool = True


def cleanup_stale_tasks(conn: sqlite3.Connection):
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

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keep connection alive, we broadcast updates from the worker
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def notify_task_update(task_id: str, progress: float, msg: str, status: str = "RUNNING", task_type: str = "pipeline"):
    await manager.broadcast({
        "task_id": task_id,
        "progress": progress,
        "msg": msg,
        "status": status,
        "task_type": task_type
    })

async def update_task_progress(task_id: str, progress: float, msg: str, task_type: str = "pipeline"):
    try:
        payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO task_queue (task_id, task_type, status, progress, payload, create_time, update_time)
                   VALUES (?, ?, 'RUNNING', ?, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                       status = 'RUNNING',
                       progress = excluded.progress,
                       update_time = excluded.update_time""",
                (task_id, task_type, progress, payload_str, now, now)
            )
        await notify_task_update(task_id, progress, msg, "RUNNING", task_type)
    except Exception as e:
        logger.error(f"Error updating task: {e}")

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

        payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
        with get_db_connection() as conn:
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
    background_tasks.add_task(_background_pipeline_worker, task_id, req)
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
        payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
        with get_db_connection() as conn:
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
    background_tasks.add_task(_background_batch_worker, task_id, req)
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
        payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
        with get_db_connection() as conn:
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
    background_tasks.add_task(_background_download_worker, task_id, req)
    return {"task_id": task_id, "status": "started"}

async def _background_creator_download_worker(task_id: str, uid: str, mode: str = "incremental"):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, f"creator_sync_{mode}")

    try:
        from media_tools.douyin.core.following_mgr import get_user
        from media_tools.douyin.core.downloader import download_by_url

        user = get_user(uid)
        if not user:
            raise RuntimeError(f"Creator not found: {uid}")

        sec_user_id = user.get("sec_user_id") or ""
        if sec_user_id.startswith("MS4w"):
            url = f"https://www.douyin.com/user/{sec_user_id}"
        else:
            url = f"https://www.douyin.com/user/{uid}"

        display_name = user.get("nickname") or uid
        await _progress_fn(0.05, f"开始同步 {display_name} 的视频（{mode}）...")

        skip_existing = mode != "full"
        result = await asyncio.to_thread(download_by_url, url, None, False, skip_existing)
        if not isinstance(result, dict) or not result.get("success"):
            raise RuntimeError(f"下载失败: {display_name}")

        new_count = len(result.get("new_files", []) or [])
        msg = f"{display_name} 同步完成：{new_count} 个新视频（{mode}）"
        payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
        with get_db_connection() as conn:
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
    background_tasks.add_task(_background_creator_download_worker, task_id, req.uid, req.mode)
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
            payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
            with get_db_connection() as conn:
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
        payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
        with get_db_connection() as conn:
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
    background_tasks.add_task(_background_full_sync_worker, task_id, req.mode)
    return {"task_id": task_id, "status": "started"}


# --- Local transcribe ---

class LocalTranscribeRequest(BaseModel):
    file_paths: List[str]
    delete_after: bool = False

class ScanDirectoryRequest(BaseModel):
    directory: str

async def _background_local_transcribe_worker(task_id: str, req: LocalTranscribeRequest):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, "local_transcribe")

    try:
        from media_tools.pipeline.worker import run_local_transcribe
        result = await asyncio.to_thread(
            run_local_transcribe,
            req.file_paths,
            None,
            req.delete_after,
        )
        s_count = result.get("success_count", 0)
        f_count = result.get("failed_count", 0)
        total = result.get("total", 0)
        msg = "没有找到有效的视频文件" if total == 0 else f"本地转写完成：成功 {s_count} 个，失败 {f_count} 个"
        payload_str = json.dumps({"msg": msg}, ensure_ascii=False)
        with get_db_connection() as conn:
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
    await _create_task(task_id, "local_transcribe", {"file_paths": req.file_paths, "delete_after": req.delete_after})
    background_tasks.add_task(_background_local_transcribe_worker, task_id, req)
    return {"task_id": task_id, "status": "started"}

@router.post("/transcribe/scan")
def scan_directory(req: ScanDirectoryRequest):
    from pathlib import Path
    dir_path = Path(req.directory)
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="目录不存在")
    extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm'}
    files = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            files.append({"path": str(f), "name": f.name, "size_mb": round(f.stat().st_size / 1024 / 1024, 1)})
    return {"directory": str(dir_path), "files": files}
