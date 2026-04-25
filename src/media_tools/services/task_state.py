import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from media_tools.douyin.core.cancel_registry import clear_cancel_event
from media_tools.db.core import get_db_connection
from media_tools.services.task_ops import notify_task_update

logger = logging.getLogger(__name__)

_active_tasks: dict[str, asyncio.Task] = {}
_background_tasks: set[asyncio.Task] = set()
MAX_AUTO_RETRY = 2


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


async def _handle_auto_retry(task_id: str):
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

        try:
            original_params = json.loads(payload_str) if payload_str else {}
        except (json.JSONDecodeError, TypeError):
            original_params = {}

        retry_count = original_params.get("_retry_count", 0)
        if retry_count >= MAX_AUTO_RETRY:
            logger.info(f"任务 {task_id} 已达最大自动重试次数 ({MAX_AUTO_RETRY})")
            return

        original_params["_retry_count"] = retry_count + 1
        payload_str = json.dumps({**original_params, "msg": f"自动重试 ({retry_count + 1}/{MAX_AUTO_RETRY})..."}, ensure_ascii=False)

        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status='RUNNING', progress=0.0, auto_retry=1, payload=? WHERE task_id=?",
                (payload_str, task_id)
            )

        logger.info(f"任务 {task_id} 失败，自动重试 ({retry_count + 1}/{MAX_AUTO_RETRY})...")
        # 延迟导入避免循环依赖
        from media_tools.api.routers.tasks import _start_task_worker
        await _start_task_worker(task_id, task_type, original_params)

    except (sqlite3.Error, OSError, RuntimeError, asyncio.TimeoutError):
        logger.exception(f"自动重试失败 task_id={task_id}")


def _register_background_task(task_id: str, coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _active_tasks[task_id] = task
    _background_tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        _active_tasks.pop(task_id, None)
        _background_tasks.discard(t)
        clear_cancel_event(task_id)

        if not t.cancelled() and t.done():
            try:
                exc = t.exception()
                if exc is not None:
                    logger.error(f"Background task {task_id} crashed: {exc!r}")
                    retry_task = asyncio.create_task(_handle_auto_retry(task_id))
                    _background_tasks.add(retry_task)
                    retry_task.add_done_callback(lambda t: _background_tasks.discard(t))
            except (RuntimeError, TypeError) as e:
                logger.exception(f"检查 task exception 失败 task_id={task_id}: {e}")

    task.add_done_callback(_on_done)
    return task
