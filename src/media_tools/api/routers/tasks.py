import asyncio
import sqlite3
import json
import logging
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Any, List, Set
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
        # 连接生命周期统计
        self._stats = {"connected": 0, "disconnected": 0, "broadcast_success": 0, "broadcast_failed": 0}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self._stats["connected"] += 1

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self._stats["disconnected"] += 1

    def get_stats(self) -> dict:
        """返回连接统计"""
        return {
            "active_connections": len(self.active_connections),
            **self._stats
        }

    async def broadcast(self, message: dict):
        """广播消息给所有活跃连接"""
        # 先检查并清理关闭的连接
        dead_connections = []
        for conn in self.active_connections:
            try:
                # 检查连接是否仍然打开
                if not hasattr(conn, 'closed') or conn.closed:
                    dead_connections.append(conn)
            except Exception:
                dead_connections.append(conn)

        for conn in dead_connections:
            self.disconnect(conn)

        # 广播
        for connection in list(self.active_connections):  # 复制列表避免迭代中修改
            try:
                await connection.send_json(message)
                self._stats["broadcast_success"] += 1
            except Exception as e:
                # 区分异常类型
                from starlette.websockets import WebSocketClose
                if isinstance(e, (WebSocketClose, ConnectionResetError, OSError, BrokenPipeError)):
                    # 连接已关闭/重置，移除该连接
                    logger.info(f"WebSocket 连接已关闭，移除连接: {id(connection)}")
                    self.disconnect(connection)
                    self._stats["broadcast_failed"] += 1
                else:
                    # 其他异常，记录错误但不移除连接
                    logger.error(f"WebSocket 广播失败: {e}")
                    self._stats["broadcast_failed"] += 1

manager = ConnectionManager()

# --- Active-task registry -----------------------------------------------------
# Tracks the asyncio.Task handle for every background worker currently running,
# keyed by task_id. Populated by _register_background_task, auto-evicted by
# add_done_callback. Enables POST /tasks/{id}/cancel to actually interrupt work.
# Also tracks all background tasks in a set to prevent GC of unreferenced tasks.
_active_tasks: dict[str, "asyncio.Task[Any]"] = {}  # type: ignore[type-arg]
_background_tasks: "set[asyncio.Task[Any]]" = set()  # type: ignore[type-arg]
MAX_AUTO_RETRY = 2  # 最大自动重试次数


async def _handle_auto_retry(task_id: str):
    """处理失败任务的自动重试"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT task_type, payload, auto_retry FROM task_queue WHERE task_id = ?",
                (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                return

            task_type = row["task_type"]
            payload_str = row["payload"]
            auto_retry = row["auto_retry"] or 0

        if not auto_retry:
            return

        # 检查当前重试次数
        try:
            original_params = json.loads(payload_str) if payload_str else {}
        except Exception:
            original_params = {}

        retry_count = original_params.get("_retry_count", 0)
        if retry_count >= MAX_AUTO_RETRY:
            logger.info(f"任务 {task_id} 已达最大自动重试次数 ({MAX_AUTO_RETRY})")
            return

        # 增加重试计数并重新运行
        original_params["_retry_count"] = retry_count + 1
        payload_str = json.dumps({**original_params, "msg": f"自动重试 ({retry_count + 1}/{MAX_AUTO_RETRY})..."}, ensure_ascii=False)

        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status='RUNNING', progress=0.0, auto_retry=1, payload=? WHERE task_id=?",
                (payload_str, task_id)
            )
            conn.commit()

        # 重新启动任务
        logger.info(f"任务 {task_id} 失败，自动重试 ({retry_count + 1}/{MAX_AUTO_RETRY})...")
        await _start_task_worker(task_id, task_type, original_params)

    except Exception:
        # 自动重试失败必须记录堆栈，否则难以排查
        logger.exception(f"自动重试失败 task_id={task_id}")


def _register_background_task(task_id: str, coro) -> "asyncio.Task[Any]":  # type: ignore[type-arg]
    task = asyncio.create_task(coro)
    _active_tasks[task_id] = task
    _background_tasks.add(task)

    def _on_done(t: "asyncio.Task[Any]") -> None:  # type: ignore[type-arg]
        _active_tasks.pop(task_id, None)
        _background_tasks.discard(t)

        # 检查任务是否失败，如果是则触发自动重试
        if not t.cancelled() and t.done():
            try:
                exc = t.exception()
                if exc is not None:
                    logger.error(f"Background task {task_id} crashed: {exc!r}")
                    # 触发自动重试，并跟踪任务防止 GC
                    retry_task = asyncio.create_task(_handle_auto_retry(task_id))
                    _background_tasks.add(retry_task)
                    retry_task.add_done_callback(lambda t: _background_tasks.discard(t))
            except Exception as e:
                logger.exception(f"检查 task exception 失败 task_id={task_id}: {e}")

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
                except Exception as e:
                    logger.warning(f"WebSocket ping failed: {e}")
                    break
        except asyncio.CancelledError:
            # 正常取消，不记录
            logger.debug("Heartbeat task cancelled")
        except Exception:
            logger.exception("Heartbeat task unexpected error")

    # 跟踪所有后台任务，防止 GC 导致静默失败
    heartbeat_task = asyncio.create_task(_heartbeat())
    _background_tasks.add(heartbeat_task)
    heartbeat_task.add_done_callback(lambda t: _background_tasks.discard(t))

    try:
        while True:
            # Just keep connection alive, we broadcast updates from the worker
            # 注意：同一时间只能有一个 coroutine 调用 receive_text()
            data = await websocket.receive_text()
            # 可以在这里处理收到的消息（如 pong/ACK）
            if data:
                logger.debug(f"WebSocket received: {data[:50]}...")
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

async def _complete_task(task_id: str, task_type: str, msg: str, status: str = "COMPLETED", error_msg: str | None = None) -> None:
    """Update task row to completed status and broadcast WebSocket notification."""
    with get_db_connection() as conn:
        payload_str = _merge_payload_from_db(conn, task_id, msg)
        conn.execute(
            "UPDATE task_queue SET status=?, progress=1.0, payload=?, error_msg=? WHERE task_id=?",
            (status, payload_str, error_msg, task_id),
        )
    await notify_task_update(task_id, 1.0, msg, status, task_type)


async def _fail_task(task_id: str, task_type: str, error: str) -> None:
    """Update task row to failed status and broadcast WebSocket notification."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?",
            (str(error), task_id),
        )
    await notify_task_update(task_id, 0.0, str(error), "FAILED", task_type)


async def _background_pipeline_worker(task_id: str, req: PipelineRequest):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, "pipeline")

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


@router.delete("/history")
def clear_task_history():
    """清除已完成/失败/取消的历史任务"""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED')"
            )
            conn.commit()
        return {"status": "success", "message": "历史任务已清除"}
    except Exception as e:
        logger.exception("clear_task_history failed")
        return {"status": "error", "message": str(e)}

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


@router.post("/{task_id}/auto-retry")
async def set_auto_retry(task_id: str, enabled: bool = True):
    """启用/禁用任务的自动重试"""
    try:
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET auto_retry = ? WHERE task_id = ?", (1 if enabled else 0, task_id))
            conn.commit()
        return {"status": "success", "message": f"自动重试已{'启用' if enabled else '禁用'}"}
    except Exception as e:
        logger.exception(f"set_auto_retry failed for {task_id}")
        return {"status": "error", "message": str(e)}


@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    """暂停一个正在运行的任务（暂仅支持 B站）"""
    try:
        # 检查任务存在且正在运行
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT status, task_type FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "message": "Task not found"}
            if row["status"] != "RUNNING":
                return {"status": "error", "message": f"Task is not running (current: {row['status']})"}
            task_type = row["task_type"]

        # 抖音下载使用 F2，不支持暂停；B站可以暂停
        if task_type in ("pipeline", "download", "sync"):
            try:
                from media_tools.bilibili.core.downloader import pause_task as pause_bilibili_download
                pause_bilibili_download(task_id)

                with get_db_connection() as conn:
                    conn.execute("UPDATE task_queue SET status = 'PAUSED', update_time = ? WHERE task_id = ?",
                               (datetime.now().isoformat(), task_id))
                    conn.commit()
                return {"status": "success", "message": "Task paused"}
            except Exception:
                pass

        return {"status": "error", "message": "当前下载器不支持暂停"}

    except Exception as e:
        logger.exception(f"pause_task failed for {task_id}")
        return {"status": "error", "message": str(e)}


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    """恢复一个已暂停的任务（暂仅支持 B站）"""
    try:
        # 检查任务存在且已暂停
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT status, task_type FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "message": "Task not found"}
            if row["status"] != "PAUSED":
                return {"status": "error", "message": f"Task is not paused (current: {row['status']})"}
            task_type = row["task_type"]

        # 抖音下载使用 F2，不支持恢复；B站可以恢复
        if task_type in ("pipeline", "download", "sync"):
            try:
                from media_tools.bilibili.core.downloader import resume_task as resume_bilibili_download
                resume_bilibili_download(task_id)

                with get_db_connection() as conn:
                    conn.execute("UPDATE task_queue SET status = 'RUNNING', update_time = ? WHERE task_id = ?",
                               (datetime.now().isoformat(), task_id))
                    conn.commit()
                return {"status": "success", "message": "Task resumed"}
            except Exception:
                pass

        return {"status": "error", "message": "当前下载器不支持恢复"}

    except Exception as e:
        logger.exception(f"resume_task failed for {task_id}")
        return {"status": "error", "message": str(e)}


@router.post("/{task_id}/rerun")
async def rerun_task(task_id: str):
    """用同一个 task_id 重新运行任务（用于崩溃后继续）。"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT task_type, payload, status FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "message": "Task not found"}

            task_type = row["task_type"]
            payload_str = row["payload"]
            current_status = row["status"]

        # 只有 FAILED/CANCELLED/PAUSED 状态才能重新运行
        if current_status not in ("FAILED", "CANCELLED", "PAUSED"):
            return {"status": "error", "message": f"当前状态 {current_status} 不能重新运行"}

        # 解析参数
        try:
            original_params = json.loads(payload_str) if payload_str else {}
        except Exception:
            original_params = {}
        original_params.pop("msg", None)

        # 重置任务状态为 RUNNING
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status='RUNNING', progress=0.0, error_msg=NULL, update_time=? WHERE task_id=?",
                (datetime.now().isoformat(), task_id)
            )
            conn.commit()

        # 用同一个 task_id 重新执行（这样可以利用断点续传）
        return await _start_task_worker(task_id, task_type, original_params)

    except Exception as e:
        logger.exception(f"rerun_task failed for {task_id}")
        return {"status": "error", "message": str(e)}


async def _start_task_worker(task_id: str, task_type: str, original_params: dict[str, Any]):
    """根据 task_type 启动对应的 worker。"""
    if task_type == "pipeline" and "url" in original_params:
        req = PipelineRequest(
            url=original_params.get("url", ""),
            max_counts=original_params.get("max_counts", 5),
            auto_delete=original_params.get("auto_delete", True)
        )
        _register_background_task(task_id, _background_pipeline_worker(task_id, req))
        return {"task_id": task_id, "status": "started", "message": "Pipeline task rerun"}

    elif task_type == "pipeline" and "video_urls" in original_params:
        batch_req = BatchPipelineRequest(
            video_urls=original_params.get("video_urls", []),
            auto_delete=original_params.get("auto_delete", True)
        )
        _register_background_task(task_id, _background_batch_worker(task_id, batch_req))
        return {"task_id": task_id, "status": "started", "message": "Batch pipeline task rerun"}

    elif task_type == "download" and "video_urls" in original_params:
        dl_req = DownloadBatchRequest(video_urls=original_params.get("video_urls", []))
        _register_background_task(task_id, _background_download_worker(task_id, dl_req))
        return {"task_id": task_id, "status": "started", "message": "Download task rerun"}

    elif task_type.startswith("creator_sync") and "uid" in original_params:
        uid = str(original_params.get("uid", ""))
        mode = str(original_params.get("mode", "incremental"))
        batch_size: int | None = original_params.get("batch_size")
        _register_background_task(task_id, _background_creator_download_worker(task_id, uid, mode, batch_size))
        return {"task_id": task_id, "status": "started", "message": "Creator sync task rerun"}

    elif task_type.startswith("full_sync") and "mode" in original_params:
        mode = str(original_params.get("mode", "incremental"))
        _register_background_task(task_id, _background_full_sync_worker(task_id, mode))
        return {"task_id": task_id, "status": "started", "message": "Full sync task rerun"}

    elif task_type == "local_transcribe" and "file_paths" in original_params:
        local_req = LocalTranscribeRequest(
            file_paths=original_params.get("file_paths", []),
            delete_after=original_params.get("delete_after", False),
            directory_root=original_params.get("directory_root")
        )
        _register_background_task(task_id, _background_local_transcribe_worker(task_id, local_req))
        return {"task_id": task_id, "status": "started", "message": "Local transcribe task rerun"}

    else:
        return {"status": "error", "message": f"Unsupported task type: {task_type}"}


@router.post("/{task_id}/retry")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    """Retry a failed task using original parameters from payload (creates NEW task)."""
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
            batch_req = BatchPipelineRequest(
                video_urls=original_params.get("video_urls", []),
                auto_delete=original_params.get("auto_delete", True)
            )
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, task_type, {"video_urls": batch_req.video_urls})
            _register_background_task(new_task_id, _background_batch_worker(new_task_id, batch_req))
            return {"task_id": new_task_id, "status": "started", "message": "Batch pipeline task retry started"}

        elif task_type == "download" and "video_urls" in original_params:
            dl_req = DownloadBatchRequest(video_urls=original_params.get("video_urls", []))
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, task_type, {"video_urls": dl_req.video_urls})
            _register_background_task(new_task_id, _background_download_worker(new_task_id, dl_req))
            return {"task_id": new_task_id, "status": "started", "message": "Download task retry started"}

        elif task_type.startswith("creator_sync") and "uid" in original_params:
            uid = str(original_params.get("uid", ""))
            mode = str(original_params.get("mode", "incremental"))
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, f"creator_sync_{mode}", {"uid": uid, "mode": mode})
            _register_background_task(new_task_id, _background_creator_download_worker(new_task_id, uid, mode))
            return {"task_id": new_task_id, "status": "started", "message": "Creator download task retry started"}

        elif task_type.startswith("full_sync") and "mode" in original_params:
            mode = str(original_params.get("mode", "incremental"))
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, f"full_sync_{mode}", {"mode": mode})
            _register_background_task(new_task_id, _background_full_sync_worker(new_task_id, mode))
            return {"task_id": new_task_id, "status": "started", "message": "Full sync task retry started"}

        elif task_type == "local_transcribe" and "file_paths" in original_params:
            local_req = LocalTranscribeRequest(
                file_paths=original_params.get("file_paths", []),
                delete_after=original_params.get("delete_after", False),
                directory_root=original_params.get("directory_root")
            )
            _register_local_assets(local_req.file_paths, local_req.delete_after, local_req.directory_root)
            new_task_id = str(uuid.uuid4())
            await _create_task(new_task_id, task_type, {"file_paths": local_req.file_paths, "delete_after": local_req.delete_after})
            _register_background_task(new_task_id, _background_local_transcribe_worker(new_task_id, local_req))
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
    batch_size: int | None = None  # 每批下载数量，None=全部


class FullSyncRequest(BaseModel):
    mode: str = "incremental"
    batch_size: int | None = None  # 每批下载数量

async def _background_batch_worker(task_id: str, req: BatchPipelineRequest):
    async def _progress_fn(p, m):
        await update_task_progress(task_id, p, m, "pipeline")

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
    except Exception as e:
        await _fail_task(task_id, "pipeline", str(e))

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
            task_id=task_id,
        )
        await _complete_task(
            task_id, "download",
            f"下载完成：成功 {result.get('success_count', 0)} 个，失败 {result.get('failed_count', 0)} 个"
        )
    except Exception as e:
        await _fail_task(task_id, "download", str(e))

@router.post("/download/batch")
async def trigger_download_batch(req: DownloadBatchRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "download", {"video_urls": req.video_urls})
    _register_background_task(task_id, _background_download_worker(task_id, req))
    return {"task_id": task_id, "status": "started"}

async def _background_creator_download_worker(task_id: str, uid: str, mode: str = "incremental", batch_size: int | None = None):
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

        await _progress_fn(0.05, f"开始同步 {display_name} 的视频（{mode}，每批 {batch_size or '全部'} 个）...")

        skip_existing = mode != "full"
        batch_size = batch_size or 50  # 默认每批50个
        total_downloaded = 0
        batch_num = 1
        all_new_files: list[str] = []

        while True:
            current_batch_size = batch_size if batch_size else None
            await _progress_fn(0.1, f"第 {batch_num} 批：下载中（最多 {current_batch_size or '全部'} 个）...")

            if platform == "bilibili":
                from media_tools.bilibili.core.downloader import download_up_by_url
                from media_tools.douyin.core.config_mgr import get_config

                mid = sec_user_id or uid.split(":", 1)[-1]
                url = f"https://space.bilibili.com/{mid}"
                # 分批下载：每次下载 batch_size 个，跳过已下载的
                try:
                    result = await asyncio.to_thread(download_up_by_url, url, current_batch_size, skip_existing)
                except Exception as e:
                    error_msg = str(e)
                    if "412" in error_msg or "blocked" in error_msg.lower():
                        await _progress_fn(0.5, f"B站请求被拦截(412)，请更换IP或稍后重试")
                        raise RuntimeError(f"B站请求被拦截(412)，请更换IP或稍后重试: {error_msg}")
                    raise
                new_files = (result.get("new_files") or []) if isinstance(result, dict) else []

                config = get_config()
                if config.is_auto_transcribe() and new_files:
                    await _transcribe_files(task_id, _progress_fn, new_files, display_name, config)

            else:
                # 抖音使用 F2 下载器
                from media_tools.douyin.core.downloader import download_by_url

                if sec_user_id.startswith("MS4w"):
                    url = f"https://www.douyin.com/user/{sec_user_id}"
                else:
                    url = f"https://www.douyin.com/user/{uid}"

                result = await asyncio.to_thread(download_by_url, url, current_batch_size, False, skip_existing)

                if not isinstance(result, dict) or not result.get("success"):
                    logger.warning(f"下载批次 {batch_num} 失败: {result}")
                    break

                new_files = (result.get("new_files") or []) if isinstance(result, dict) else []

                # 立即转写这批视频
                from media_tools.douyin.core.config_mgr import get_config
                config = get_config()
                if config.is_auto_transcribe() and new_files:
                    await _transcribe_files(task_id, _progress_fn, new_files, display_name, config)

            if not new_files or not batch_size:
                # 没有更多视频或不需要分批，结束
                break

            total_downloaded += len(new_files)
            all_new_files.extend(new_files)
            batch_num += 1

            await _progress_fn(0.9, f"第 {batch_num - 1} 批完成（累计 {total_downloaded} 个），继续下一批...")

        # 更新创作者信息
        if uploader := result.get("uploader"):
            if uploader.get("nickname"):
                with get_db_connection() as conn:
                    conn.execute(
                        "UPDATE creators SET nickname = ?, homepage_url = ? WHERE uid = ?",
                        (uploader["nickname"], uploader.get("homepage_url", ""), uid),
                    )
                    conn.commit()

        msg = f"{display_name} 同步完成：共 {total_downloaded} 个新视频（{batch_num - 1} 批，{mode}）"
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg)
            conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (payload_str, task_id))
        await notify_task_update(task_id, 1.0, msg, "COMPLETED", f"creator_sync_{mode}")
    except Exception as e:
        logger.exception(f"creator_download_worker failed for {uid}")
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", f"creator_sync_{mode}")


async def _transcribe_files(task_id: str, _progress_fn, new_files: list, display_name: str, config):
    """转写一批视频文件"""
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    await _progress_fn(0.6, f"下载完成，准备转写 {len(new_files)} 个视频...")
    pipeline_config = load_pipeline_config()
    orchestrator = create_orchestrator(pipeline_config, creator_folder_override=display_name)
    delete_after = config.is_auto_delete_video()
    total = len(new_files)

    for index, file_path in enumerate(new_files, 1):
        await _progress_fn(0.6 + 0.3 * ((index - 1) / total), f"正在转写 ({index}/{total})")
        try:
            await orchestrator.transcribe_with_retry(Path(file_path))
        except Exception as e:
            logger.warning(f"转写失败 {file_path}: {e}")
        if delete_after:
            try:
                Path(file_path).unlink()
            except FileNotFoundError:
                pass  # 文件已不存在，可忽略
            except OSError as e:
                logger.error(f"删除转写后视频失败: {file_path}, {e}")

@router.post("/download/creator")
async def trigger_creator_download(req: CreatorDownloadRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, f"creator_sync_{req.mode}", {"uid": req.uid, "mode": req.mode, "batch_size": req.batch_size})
    _register_background_task(task_id, _background_creator_download_worker(task_id, req.uid, req.mode, req.batch_size))
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
        await _complete_task(task_id, "local_transcribe", msg)
    except Exception as e:
        logger.error(f"Local transcribe worker failed: {e}")
        await _fail_task(task_id, "local_transcribe", str(e))

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
