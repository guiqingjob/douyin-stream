"""任务工具函数 — WebSocket 通知、进度更新、payload 合并等。"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from typing import Any

from media_tools.repositories.task_repository import TaskRepository
from media_tools.db.core import get_db_connection

logger = logging.getLogger(__name__)

# WebSocket 连接集合
_websocket_connections: set[Any] = set()


def register_websocket(ws: Any) -> None:
    """注册 WebSocket 连接。"""
    _websocket_connections.add(ws)


def unregister_websocket(ws: Any) -> None:
    """注销 WebSocket 连接。"""
    _websocket_connections.discard(ws)


async def _broadcast_ws_message(msg: dict[str, Any]) -> None:
    """向所有 WebSocket 连接广播消息。"""
    disconnected = []
    for ws in list(_websocket_connections):
        try:
            await ws.send_json(msg)
        except (RuntimeError, OSError, ConnectionError):
            disconnected.append(ws)
    for ws in disconnected:
        _websocket_connections.discard(ws)


async def notify_task_update(
    task_id: str,
    progress: float,
    message: str,
    status: str,
    task_type: str = "pipeline",
    result_summary: dict | None = None,
    subtasks: list | None = None,
    stage: str = "",
) -> None:
    """WebSocket 广播任务更新。"""
    msg: dict[str, Any] = {
        "type": "progress",
        "task_id": task_id,
        "status": status,
        "task_type": task_type,
        "progress": progress,
        "msg": message,
        "stage": stage,
    }
    if result_summary:
        msg["result_summary"] = result_summary
    if subtasks:
        msg["subtasks"] = subtasks
    await _broadcast_ws_message(msg)


async def update_task_progress(
    task_id: str,
    progress: float,
    message: str,
    task_type: str = "pipeline",
    result_summary: dict | None = None,
    subtasks: list | None = None,
    stage: str = "",
) -> None:
    """更新任务进度并广播。"""
    now = datetime.now().isoformat()
    payload_str = _merge_payload_from_db(task_id, message, result_summary, subtasks)
    with get_db_connection() as conn:
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
    await notify_task_update(task_id, progress, message, "RUNNING", task_type, result_summary, subtasks, stage)


def _merge_task_payload(
    existing_payload: str | None,
    msg: str,
    result_summary: dict | None = None,
    subtasks: list | None = None,
) -> str:
    """合并任务 payload。"""
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
    task_id: str,
    msg: str,
    result_summary: dict | None = None,
    subtasks: list | None = None,
) -> str:
    """从数据库读取现有 payload 并合并。"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT payload FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            existing = row[0] if row else None
    except sqlite3.Error as e:
        logger.warning(f"读取任务payload失败: {e}")
        existing = None
    return _merge_task_payload(existing, msg, result_summary, subtasks)


async def _task_heartbeat(task_id: str, interval: int = 30) -> None:
    """定期心跳，防止任务被标记为过期。"""
    while True:
        await asyncio.sleep(interval)
        TaskRepository.update_heartbeat(task_id)


async def _mark_task_cancelled(task_id: str, task_type: str) -> None:
    """标记任务为已取消。"""
    TaskRepository.mark_failed(task_id, "任务已取消")
    await notify_task_update(task_id, 0.0, "任务已取消", "CANCELLED", task_type)


async def _complete_task(
    task_id: str,
    task_type: str,
    msg: str,
    result_summary: dict | None = None,
    subtasks: list | None = None,
) -> None:
    """标记任务完成。"""
    TaskRepository.mark_completed(task_id, msg, result_summary, subtasks)
    await notify_task_update(task_id, 1.0, msg, "COMPLETED", task_type, result_summary, subtasks)


async def _fail_task(task_id: str, task_type: str, error: str) -> None:
    """标记任务失败。"""
    TaskRepository.mark_failed(task_id, error)
    await notify_task_update(task_id, 0.0, error, "FAILED", task_type)
