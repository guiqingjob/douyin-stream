import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from media_tools.api.websocket_manager import manager
from media_tools.db.core import get_db_connection
from media_tools.core.config import get_runtime_setting_int
from media_tools.services.auto_retry import schedule_auto_retry
from media_tools.repositories.task_repository import _merge_task_payload, _merge_payload_from_db

logger = logging.getLogger(__name__)
DEFAULT_TASK_STALE_MINUTES = 20
UPLOAD_STAGE_STALE_MINUTES = 30


def get_task_stale_minutes() -> int:
    raw = os.environ.get("MEDIA_TOOLS_TASK_STALE_MINUTES", "").strip()
    if raw:
        try:
            minutes = int(raw)
            return minutes if minutes > 0 else DEFAULT_TASK_STALE_MINUTES
        except ValueError:
            return DEFAULT_TASK_STALE_MINUTES
    return get_runtime_setting_int("task_stale_minutes", DEFAULT_TASK_STALE_MINUTES)


def _extract_payload_pipeline_stage(payload: str | None) -> str:
    if not payload:
        return ""
    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""
    if not isinstance(parsed, dict):
        return ""
    pipeline_progress = parsed.get("pipeline_progress")
    if not isinstance(pipeline_progress, dict):
        return ""
    stage = pipeline_progress.get("stage")
    return stage.strip() if isinstance(stage, str) else ""


def _get_stale_minutes_for_stage(stage: str, default_minutes: int) -> int:
    normalized = stage.strip().lower()
    if normalized == "upload":
        return max(default_minutes, UPLOAD_STAGE_STALE_MINUTES)
    return default_minutes


def cleanup_stale_tasks(conn: sqlite3.Connection, stale_minutes: int | None = None):
    default_minutes = stale_minutes if stale_minutes is not None else get_task_stale_minutes()
    default_minutes = default_minutes if default_minutes > 0 else DEFAULT_TASK_STALE_MINUTES

    now = datetime.now()
    now_iso = now.isoformat()

    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT task_id, payload, update_time
        FROM task_queue
        WHERE status IN ('PENDING', 'RUNNING')
          AND update_time IS NOT NULL
        """
    ).fetchall()

    for row in rows:
        task_id = row["task_id"]
        update_time_raw = row["update_time"]
        try:
            last_update = datetime.fromisoformat(str(update_time_raw))
        except ValueError:
            continue

        stage = _extract_payload_pipeline_stage(row["payload"])
        minutes = _get_stale_minutes_for_stage(stage, default_minutes)
        if last_update >= (now - timedelta(minutes=minutes)):
            continue

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
            WHERE task_id = ?
              AND status IN ('PENDING', 'RUNNING')
            """,
            (now_iso, task_id),
        )

    delete_cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    conn.execute(
        "DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED') AND update_time < ?",
        (delete_cutoff,),
    )


async def notify_task_update(
    task_id: str,
    progress: float,
    msg: str,
    status: str = "RUNNING",
    task_type: str = "pipeline",
    result_summary: dict | None = None,
    subtasks: list | None = None,
    stage: str = "",
    pipeline_progress: dict | None = None,
):
    message = {
        "task_id": task_id,
        "progress": progress,
        "msg": msg,
        "status": status,
        "task_type": task_type,
        "update_time": datetime.now().isoformat(),
    }
    if stage:
        message["stage"] = stage
    if result_summary:
        message["result_summary"] = result_summary
    if subtasks:
        message["subtasks"] = subtasks[-20:]
    if pipeline_progress:
        message["pipeline_progress"] = pipeline_progress
    await manager.broadcast(message)


# _merge_task_payload 和 _merge_payload_from_db 从 task_repository.py 导入，消除重复代码


async def update_task_progress(
    task_id: str,
    progress: float,
    msg: str,
    task_type: str = "pipeline",
    result_summary: dict | None = None,
    subtasks: list | None = None,
    stage: str = "",
    pipeline_progress: dict | None = None,
):
    try:
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT status FROM task_queue WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row and row["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                return

            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, subtasks)
            if stage or pipeline_progress:
                try:
                    parsed = json.loads(payload_str) if payload_str else {}
                except (json.JSONDecodeError, TypeError, ValueError):
                    parsed = {}
                if isinstance(parsed, dict):
                    pp = parsed.get("pipeline_progress")
                    if not isinstance(pp, dict):
                        pp = {}
                    if stage:
                        pp["stage"] = stage
                    if pipeline_progress:
                        pp.update(pipeline_progress)
                    parsed["pipeline_progress"] = pp
                    payload_str = json.dumps(parsed, ensure_ascii=False)
            if row is None:
                conn.execute(
                    """INSERT INTO task_queue (task_id, task_type, status, progress, payload, create_time, update_time)
                       VALUES (?, ?, 'RUNNING', ?, ?, ?, ?)""",
                    (task_id, task_type, progress, payload_str, now, now),
                )
            else:
                conn.execute(
                    """UPDATE task_queue
                       SET status='RUNNING', progress=?, payload=?, update_time=?
                       WHERE task_id=? AND status IN ('PENDING', 'RUNNING', 'PAUSED')""",
                    (progress, payload_str, now, task_id),
                )
        await notify_task_update(task_id, progress, msg, "RUNNING", task_type, result_summary, subtasks, stage, pipeline_progress)
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
    progress = 1.0 if status == "COMPLETED" else 0.0
    try:
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, subtasks)
            conn.execute(
                "UPDATE task_queue SET status=?, progress=?, payload=?, error_msg=? WHERE task_id=?",
                (status, progress, payload_str, error_msg, task_id),
            )
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error(f"Failed to complete task {task_id} in DB: {e}")
    await notify_task_update(task_id, progress, msg, status, task_type, result_summary, subtasks)
    if status == "FAILED":
        schedule_auto_retry(task_id)


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
    schedule_auto_retry(task_id)
