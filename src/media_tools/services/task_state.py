import asyncio
import logging
import sqlite3
from datetime import datetime
from media_tools.core import background
from media_tools.douyin.core.cancel_registry import clear_cancel_event
from media_tools.db.core import get_db_connection
from media_tools.services.auto_retry import schedule_auto_retry

logger = logging.getLogger(__name__)

_active_tasks: dict[str, asyncio.Task] = {}


async def _task_heartbeat(task_id: str, interval: int = 30):
    while True:
        await asyncio.sleep(interval)
        try:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE task_queue SET update_time = ? WHERE task_id = ? AND status IN ('PENDING', 'RUNNING')",
                    (datetime.now().isoformat(), task_id),
                )
        except (sqlite3.Error, OSError) as e:
            logger.warning(f"heartbeat DB更新失败 task_id={task_id}: {e}")


def _register_background_task(task_id: str, coro) -> asyncio.Task:
    task = background.create(coro, name=f"worker:{task_id}")
    _active_tasks[task_id] = task

    def _on_done(t: asyncio.Task) -> None:
        _active_tasks.pop(task_id, None)
        clear_cancel_event(task_id)

        if not t.cancelled() and t.done():
            try:
                exc = t.exception()
                if exc is not None:
                    logger.error(f"Background task {task_id} crashed: {exc!r}")
                    schedule_auto_retry(task_id)
            except (RuntimeError, TypeError) as e:
                logger.exception(f"检查 task exception 失败 task_id={task_id}: {e}")

    task.add_done_callback(_on_done)
    return task
