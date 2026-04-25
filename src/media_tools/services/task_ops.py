import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from media_tools.api.websocket_manager import manager
from media_tools.db.core import get_db_connection

logger = logging.getLogger(__name__)
STALE_TASK_HOURS = 2


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

    delete_cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    conn.execute(
        "DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED') AND update_time < ?",
        (delete_cutoff,),
    )

    deleted_assets = conn.execute("SELECT asset_id FROM media_assets WHERE video_status='deleted'").fetchall()
    if deleted_assets:
        deleted_ids = [row[0] for row in deleted_assets]
        placeholders = ",".join("?" * len(deleted_ids))
        conn.execute(f"DELETE FROM assets_fts WHERE asset_id IN ({placeholders})", deleted_ids)
        conn.execute(f"DELETE FROM media_assets WHERE asset_id IN ({placeholders})", deleted_ids)
        logger.info(f"Cleaned up {len(deleted_ids)} deleted media assets")

    stale_pending_cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    stale_assets = conn.execute(
        "SELECT asset_id FROM media_assets WHERE transcript_status='pending' AND create_time < ?",
        (stale_pending_cutoff,)
    ).fetchall()
    if stale_assets:
        stale_ids = [row[0] for row in stale_assets]
        placeholders = ",".join("?" * len(stale_ids))
        conn.execute(f"DELETE FROM assets_fts WHERE asset_id IN ({placeholders})", stale_ids)
        conn.execute(f"DELETE FROM media_assets WHERE asset_id IN ({placeholders})", stale_ids)
        logger.info(f"Cleaned up {len(stale_ids)} stale pending media assets")

    conn.commit()


async def notify_task_update(
    task_id: str,
    progress: float,
    msg: str,
    status: str = "RUNNING",
    task_type: str = "pipeline",
    result_summary: dict | None = None,
    subtasks: list | None = None,
    stage: str = "",
):
    message = {
        "task_id": task_id,
        "progress": progress,
        "msg": msg,
        "status": status,
        "task_type": task_type,
    }
    if stage:
        message["stage"] = stage
    if result_summary:
        message["result_summary"] = result_summary
    if subtasks:
        message["subtasks"] = subtasks[-20:]
    await manager.broadcast(message)


def _merge_task_payload(
    existing_payload: str | None,
    msg: str,
    result_summary: dict | None = None,
    subtasks: list | None = None,
) -> str:
    base_payload: dict = {}
    if existing_payload:
        try:
            parsed = json.loads(existing_payload)
            if isinstance(parsed, dict):
                base_payload = parsed
        except (json.JSONDecodeError, TypeError):
            base_payload = {}
    base_payload["msg"] = msg
    if result_summary:
        base_payload["total"] = result_summary.get("total", 0)
        base_payload["completed"] = result_summary.get("success", 0)
        base_payload["failed"] = result_summary.get("failed", 0)
        base_payload["result_summary"] = result_summary
    if subtasks:
        base_payload["subtasks"] = subtasks[-100:]
    return json.dumps(base_payload, ensure_ascii=False)


def _merge_payload_from_db(
    conn: sqlite3.Connection,
    task_id: str,
    msg: str,
    result_summary: dict | None = None,
    subtasks: list | None = None,
) -> str:
    try:
        cursor = conn.execute("SELECT payload FROM task_queue WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        existing = row["payload"] if row else None
    except sqlite3.Error:
        existing = None
    return _merge_task_payload(existing, msg, result_summary, subtasks)


async def update_task_progress(
    task_id: str,
    progress: float,
    msg: str,
    task_type: str = "pipeline",
    result_summary: dict | None = None,
    subtasks: list | None = None,
    stage: str = "",
):
    try:
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, subtasks)
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
        await notify_task_update(task_id, progress, msg, "RUNNING", task_type, result_summary, subtasks, stage)
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error(f"Error updating task: {e}")


async def _mark_task_cancelled(task_id: str, task_type: str) -> None:
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
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error(f"Failed to mark task {task_id} as cancelled: {e}")


async def _complete_task(
    task_id: str,
    task_type: str,
    msg: str,
    status: str = "COMPLETED",
    error_msg: str | None = None,
    result_summary: dict | None = None,
    subtasks: list | None = None,
) -> None:
    try:
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, subtasks)
            conn.execute(
                "UPDATE task_queue SET status=?, progress=1.0, payload=?, error_msg=? WHERE task_id=?",
                (status, payload_str, error_msg, task_id),
            )
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error(f"Failed to complete task {task_id} in DB: {e}")
    await notify_task_update(task_id, 1.0, msg, status, task_type, result_summary, subtasks)


async def _fail_task(task_id: str, task_type: str, error: str) -> None:
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?",
                (str(error), task_id),
            )
    except (sqlite3.Error, OSError) as e:
        logger.error(f"Failed to fail task {task_id} in DB: {e}")
    await notify_task_update(task_id, 0.0, str(error), "FAILED", task_type)
