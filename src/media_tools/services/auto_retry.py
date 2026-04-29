from __future__ import annotations

import asyncio
import json
import logging
import sqlite3

from media_tools.db.core import get_db_connection

logger = logging.getLogger(__name__)

MAX_AUTO_RETRY = 2
_background_tasks: set[asyncio.Task] = set()


def schedule_auto_retry(task_id: str) -> None:
    t = asyncio.create_task(handle_auto_retry(task_id))
    _background_tasks.add(t)
    t.add_done_callback(lambda t: _background_tasks.discard(t))


async def handle_auto_retry(task_id: str) -> None:
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT task_type, payload, auto_retry FROM task_queue WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if not row:
                return
            if not (row["auto_retry"] or 0):
                return

            task_type = row["task_type"]
            payload_str = row["payload"] or ""

        try:
            original_params = json.loads(payload_str) if payload_str else {}
        except (json.JSONDecodeError, TypeError):
            original_params = {}

        retry_count = int(original_params.get("_retry_count", 0) or 0)
        if retry_count >= MAX_AUTO_RETRY:
            logger.info(f"任务 {task_id} 已达最大自动重试次数 ({MAX_AUTO_RETRY})")
            return

        original_params["_retry_count"] = retry_count + 1
        payload_str = json.dumps(
            {**original_params, "msg": f"自动重试 ({retry_count + 1}/{MAX_AUTO_RETRY})..."},
            ensure_ascii=False,
        )

        with get_db_connection() as conn:
            cursor = conn.execute(
                "UPDATE task_queue SET status='RUNNING', progress=0.0, auto_retry=1, payload=? WHERE task_id=? AND status='FAILED'",
                (payload_str, task_id),
            )
            if cursor.rowcount == 0:
                logger.info(f"任务 {task_id} 状态已变更，跳过自动重试")
                return

        from media_tools.api.routers.tasks import _start_task_worker

        await _start_task_worker(task_id, task_type, original_params)
    except (sqlite3.Error, OSError, RuntimeError, asyncio.TimeoutError):
        logger.exception(f"自动重试失败 task_id={task_id}")

