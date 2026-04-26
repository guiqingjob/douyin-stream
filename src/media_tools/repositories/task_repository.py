"""任务数据访问层 - 所有 task_queue 表的操作集中在这里"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)
from typing import Any

from media_tools.db.core import get_db_connection
from media_tools.core.workflow import validate_transition_by_str, InvalidTransitionError


def _merge_task_payload(
    existing_payload: str | None,
    msg: str,
    result_summary: dict | None = None,
    subtasks: list | None = None,
) -> str:
    """合并任务 payload，保留现有字段并更新进度信息"""
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
    """从数据库读取现有 payload 并合并新信息"""
    try:
        cursor = conn.execute("SELECT payload FROM task_queue WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        existing = row["payload"] if row else None
    except sqlite3.Error as e:
        logger.warning(f"读取任务payload失败: {e}")
        existing = None
    return _merge_task_payload(existing, msg, result_summary, subtasks)


class TaskRepository:
    """任务仓库 - task_queue 表的所有操作（含状态机验证）"""

    @staticmethod
    def _validate_transition(task_id: str, to_status: str) -> None:
        """验证状态转移是否合法，不合法则抛出 InvalidTransitionError。"""
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT status FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            from_status = row[0] if row else "PENDING"
        validate_transition_by_str(from_status, to_status)

    # ---------- CREATE ----------

    @staticmethod
    def create(task_id: str, task_type: str, payload: dict | None = None) -> None:
        """创建新任务"""
        now = datetime.now().isoformat()
        payload_str = json.dumps(payload or {}, ensure_ascii=False)
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO task_queue (task_id, task_type, status, progress, payload, create_time, update_time)
                   VALUES (?, ?, 'PENDING', 0.0, ?, ?, ?)""",
                (task_id, task_type, payload_str, now, now),
            )

    @staticmethod
    def create_running(task_id: str, task_type: str, payload: dict | None = None) -> None:
        """创建并标记为 RUNNING（用于 rerun）"""
        now = datetime.now().isoformat()
        payload_str = json.dumps(payload or {}, ensure_ascii=False)
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO task_queue (task_id, task_type, status, progress, payload, create_time, update_time)
                   VALUES (?, ?, 'RUNNING', 0.0, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                       status = 'RUNNING',
                       progress = 0.0,
                       error_msg = NULL,
                       update_time = excluded.update_time""",
                (task_id, task_type, payload_str, now, now),
            )

    # ---------- READ ----------

    @staticmethod
    def find_by_id(task_id: str) -> dict[str, Any] | None:
        """按 ID 查询任务"""
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def find_active() -> list[dict[str, Any]]:
        """查询活跃任务（PENDING 或 RUNNING）"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM task_queue WHERE status IN ('PENDING', 'RUNNING')"
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def list_recent(limit: int = 50) -> list[dict[str, Any]]:
        """查询最近更新的任务"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM task_queue ORDER BY update_time DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_status(task_id: str) -> tuple[str | None, str | None]:
        """获取任务状态和类型"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT status, task_type FROM task_queue WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if row:
                return row["status"], row["task_type"]
            return None, None

    @staticmethod
    def get_task_type_and_payload(task_id: str) -> tuple[str | None, str | None]:
        """获取任务类型和 payload"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT task_type, payload FROM task_queue WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if row:
                return row["task_type"], row["payload"]
            return None, None

    @staticmethod
    def get_task_type_payload_status(task_id: str) -> tuple[str | None, str | None, str | None]:
        """获取任务类型、payload 和状态"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT task_type, payload, status FROM task_queue WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if row:
                return row["task_type"], row["payload"], row["status"]
            return None, None, None

    @staticmethod
    def get_task_type_payload_auto_retry(task_id: str) -> tuple[str | None, str | None, bool]:
        """获取任务类型、payload 和 auto_retry"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT task_type, payload, auto_retry FROM task_queue WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if row:
                return row["task_type"], row["payload"], bool(row["auto_retry"])
            return None, None, False

    # ---------- UPDATE ----------

    @staticmethod
    def update_progress(
        task_id: str,
        progress: float,
        msg: str,
        task_type: str = "pipeline",
        result_summary: dict | None = None,
        subtasks: list | None = None,
    ) -> None:
        """更新任务进度"""
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, subtasks)
            conn.execute(
                """INSERT INTO task_queue (task_id, task_type, status, progress, payload, create_time, update_time)
                   VALUES (?, ?, 'RUNNING', ?, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                       status = 'RUNNING',
                       progress = excluded.progress,
                       payload = excluded.payload,
                       update_time = excluded.update_time""",
                (task_id, task_type, progress, payload_str, now, now),
            )

    @staticmethod
    def mark_running(task_id: str, progress: float = 0.0, payload: str | None = None) -> None:
        """标记任务为 RUNNING"""
        TaskRepository._validate_transition(task_id, "RUNNING")
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            if payload:
                conn.execute(
                    "UPDATE task_queue SET status='RUNNING', progress=?, payload=?, update_time=? WHERE task_id=?",
                    (progress, payload, now, task_id),
                )
            else:
                conn.execute(
                    "UPDATE task_queue SET status='RUNNING', progress=?, update_time=? WHERE task_id=?",
                    (progress, now, task_id),
                )

    @staticmethod
    def mark_completed(
        task_id: str,
        msg: str,
        result_summary: dict | None = None,
        subtasks: list | None = None,
    ) -> None:
        """标记任务为 COMPLETED"""
        TaskRepository._validate_transition(task_id, "COMPLETED")
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, subtasks)
            conn.execute(
                "UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=?, update_time=? WHERE task_id=?",
                (payload_str, now, task_id),
            )

    @staticmethod
    def mark_failed(task_id: str, error: str) -> None:
        """标记任务为 FAILED"""
        TaskRepository._validate_transition(task_id, "FAILED")
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?",
                (str(error), task_id),
            )

    @staticmethod
    def update_heartbeat(task_id: str) -> None:
        """更新任务心跳时间"""
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET update_time = ? WHERE task_id = ? AND status IN ('PENDING', 'RUNNING')",
                (now, task_id),
            )

    @staticmethod
    def set_auto_retry(task_id: str, enabled: bool) -> None:
        """设置自动重试"""
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET auto_retry = ? WHERE task_id = ?",
                (1 if enabled else 0, task_id),
            )

    # ---------- DELETE ----------

    @staticmethod
    def delete(task_id: str) -> None:
        """删除单个任务"""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM task_queue WHERE task_id = ?", (task_id,))

    @staticmethod
    def clear_history(hours: int = 2) -> None:
        """清除历史任务"""
        cutoff = datetime.now() - __import__('datetime').timedelta(hours=hours)
        with get_db_connection() as conn:
            conn.execute(
                "DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED') AND update_time < ?",
                (cutoff.isoformat(),),
            )

    @staticmethod
    def clear_all_history() -> None:
        """清除所有已完成/失败/取消的任务"""
        with get_db_connection() as conn:
            conn.execute(
                "DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED')",
            )
