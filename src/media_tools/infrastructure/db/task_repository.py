"""SQLite TaskRepository 实现"""
from datetime import datetime, timedelta
from typing import List, Optional

from media_tools.db.core import get_db_connection
from media_tools.domain.entities.task import Task, TaskStatus, TaskType
from media_tools.domain.repositories.task_repository import TaskRepository


class SQLiteTaskRepository(TaskRepository):
    """SQLite 任务仓储实现"""

    def save(self, task: Task) -> None:
        """保存任务"""
        import json

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO task_queue (
                    task_id, task_type, status, progress, payload, error_msg,
                    create_time, update_time, start_time, end_time,
                    cancel_requested, auto_retry
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.task_type.value,
                    task.status.value,
                    task.progress,
                    json.dumps(task.payload, ensure_ascii=False),
                    task.error_msg,
                    task.create_time.isoformat(),
                    task.update_time.isoformat(),
                    task.start_time.isoformat() if task.start_time else None,
                    task.end_time.isoformat() if task.end_time else None,
                    task.cancel_requested,
                    task.auto_retry,
                ),
            )

    def find_by_id(self, task_id: str) -> Optional[Task]:
        """按 ID 查询任务"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            row = conn.execute(
                "SELECT * FROM task_queue WHERE task_id = ? LIMIT 1",
                (task_id,),
            ).fetchone()
            return Task.from_dict(row) if row else None

    def find_active(self) -> List[Task]:
        """查询活跃任务"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM task_queue WHERE status IN (?, ?)",
                (TaskStatus.PENDING.value, TaskStatus.RUNNING.value),
            ).fetchall()
            return [Task.from_dict(row) for row in rows]

    def find_all(self) -> List[Task]:
        """查询所有任务"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute("SELECT * FROM task_queue ORDER BY update_time DESC").fetchall()
            return [Task.from_dict(row) for row in rows]

    def find_recent(self, limit: int = 50) -> List[Task]:
        """查询最近的任务"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM task_queue ORDER BY update_time DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [Task.from_dict(row) for row in rows]

    def find_by_type(self, task_type: str) -> List[Task]:
        """按类型查询任务"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM task_queue WHERE task_type = ? ORDER BY update_time DESC",
                (task_type,),
            ).fetchall()
            return [Task.from_dict(row) for row in rows]

    def find_by_status(self, status: str) -> List[Task]:
        """按状态查询任务"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM task_queue WHERE status = ? ORDER BY update_time DESC",
                (status,),
            ).fetchall()
            return [Task.from_dict(row) for row in rows]

    def delete(self, task_id: str) -> None:
        """删除任务"""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM task_queue WHERE task_id = ?", (task_id,))

    def exists(self, task_id: str) -> bool:
        """检查任务是否存在"""
        with get_db_connection() as conn:
            row = conn.execute("SELECT 1 FROM task_queue WHERE task_id = ?", (task_id,)).fetchone()
            return row is not None

    def update_progress(self, task_id: str, progress: float, msg: str) -> None:
        """更新任务进度"""
        task = self.find_by_id(task_id)
        if task and not task.is_terminal():
            task.update_progress(progress, msg)
            self.save(task)

    def clear_history(self, hours: int = 2) -> None:
        """清除历史任务"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        with get_db_connection() as conn:
            conn.execute(
                """
                DELETE FROM task_queue
                WHERE status IN (?, ?, ?) AND update_time < ?
                """,
                (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value, cutoff),
            )

    def count_by_status(self) -> dict:
        """按状态统计任务数量"""
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM task_queue GROUP BY status"
            ).fetchall()
            return {row[0]: row[1] for row in rows}


def create_task_repository() -> TaskRepository:
    """创建 TaskRepository 实例"""
    return SQLiteTaskRepository()