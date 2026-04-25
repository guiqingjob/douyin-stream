"""任务服务层 — 任务管理的业务逻辑，不含 FastAPI/WebSocket 代码。"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from media_tools.core.config import get_runtime_setting_bool
from media_tools.db.core import get_db_connection
from media_tools.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)
STALE_TASK_HOURS = 2


def cleanup_stale_tasks() -> dict[str, int]:
    """清理过期任务，返回统计信息。"""
    with get_db_connection() as conn:
        # Mark stale PENDING/RUNNING tasks as FAILED
        cutoff = (datetime.now() - timedelta(hours=STALE_TASK_HOURS)).isoformat()
        cursor = conn.execute(
            """
            UPDATE task_queue
            SET status = 'FAILED',
                progress = 0.0,
                error_msg = COALESCE(NULLIF(error_msg, ''), '任务长时间没有更新，已自动标记为失败，请重新发起。'),
                update_time = ?
            WHERE status IN ('PENDING', 'RUNNING')
              AND update_time IS NOT NULL
              AND update_time < ?
            """,
            (datetime.now().isoformat(), cutoff),
        )
        stale_count = cursor.rowcount

        # Delete old completed tasks (older than 7 days)
        delete_cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        cursor = conn.execute(
            "DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED') AND update_time < ?",
            (delete_cutoff,),
        )
        deleted_count = cursor.rowcount

        conn.commit()

    return {"stale_marked": stale_count, "old_deleted": deleted_count}


def get_task_history(limit: int = 50) -> list[dict[str, Any]]:
    """获取任务历史列表。"""
    return TaskRepository.list_recent(limit)


def get_task_status(task_id: str) -> dict[str, Any] | None:
    """获取单个任务状态。"""
    return TaskRepository.find_by_id(task_id)


def delete_task(task_id: str) -> bool:
    """删除单个任务。"""
    TaskRepository.delete(task_id)
    return True


def clear_task_history() -> dict[str, str]:
    """清除历史任务。"""
    TaskRepository.clear_all_history()
    return {"status": "success", "message": "历史任务已清除"}


def pause_task(task_id: str) -> dict[str, str]:
    """暂停任务。"""
    with get_db_connection() as conn:
        conn.execute("UPDATE task_queue SET status='PAUSED' WHERE task_id=?", (task_id,))
        conn.commit()
    return {"status": "success", "message": "任务已暂停"}


def resume_task(task_id: str) -> dict[str, str]:
    """恢复任务。"""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE task_queue SET status='RUNNING' WHERE task_id=? AND status='PAUSED'",
            (task_id,),
        )
        conn.commit()
    return {"status": "success", "message": "任务已恢复"}


def set_auto_retry(task_id: str, enabled: bool) -> dict[str, str]:
    """设置自动重试。"""
    TaskRepository.set_auto_retry(task_id, enabled)
    return {"status": "success", "message": f"自动重试已{'开启' if enabled else '关闭'}"}


def create_task(task_id: str, task_type: str, payload: dict | None = None) -> None:
    """创建新任务。"""
    TaskRepository.create(task_id, task_type, payload)


def get_auto_transcribe() -> bool:
    """获取自动转写配置。"""
    return get_runtime_setting_bool("auto_transcribe", False)


def get_auto_delete() -> bool:
    """获取自动删除配置。"""
    return get_runtime_setting_bool("auto_delete", True)
