"""
后台任务队列组件 - 基于 SQLite 的轻量任务状态管理

本轮重构目标：
1. 任务状态按 task_id 绑定，避免“最新任务”串页/串状态
2. 页面可按 task_type 过滤读取任务
3. 修复“清除状态”无效的问题
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Callable, Iterable

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger

logger = get_logger("web")

_TASK_CONTEXT = threading.local()
_CANCEL_EVENTS: dict[str, threading.Event] = {}
_CANCEL_LOCK = threading.Lock()


def _get_db_path():
    return get_config().get_db_path()


def _normalize_task_types(task_types: str | Iterable[str] | None) -> list[str] | None:
    if task_types is None:
        return None
    if isinstance(task_types, str):
        return [task_types]
    normalized = [task_type for task_type in task_types if task_type]
    return normalized or None


def _build_filters(
    task_types: str | Iterable[str] | None = None,
    *,
    active_only: bool = False,
) -> tuple[str, list[Any]]:
    filters: list[str] = []
    params: list[Any] = []

    normalized = _normalize_task_types(task_types)
    if normalized:
        placeholders = ", ".join("?" for _ in normalized)
        filters.append(f"task_type IN ({placeholders})")
        params.extend(normalized)

    if active_only:
        filters.append("status IN ('PENDING', 'RUNNING')")

    if not filters:
        return "", params
    return " WHERE " + " AND ".join(filters), params


def _parse_payload(payload_raw: str | None) -> dict[str, Any]:
    if not payload_raw:
        return {}
    try:
        return json.loads(payload_raw)
    except Exception:
        return {}


def _row_to_task(row) -> dict[str, Any]:
    payload = _parse_payload(row[2])
    return {
        "task_id": row[0],
        "task_type": row[1],
        "description": payload.get("description", ""),
        "status": (row[3] or "pending").lower(),
        "progress": row[4] or 0.0,
        "message": payload.get("message", ""),
        "result": payload.get("result"),
        "error": row[5] or payload.get("error"),
        "created_at": row[6],
        "updated_at": row[7],
        "completed_at": payload.get("completed_at"),
    }


def _load_task_by_id(task_id: str) -> dict[str, Any] | None:
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT task_id, task_type, payload, status, progress, error_msg, create_time, update_time
                FROM task_queue
                WHERE task_id = ?
                LIMIT 1
                """,
                (task_id,),
            )
            row = cursor.fetchone()
            return _row_to_task(row) if row else None
    except Exception as exc:
        logger.error(f"按 ID 读取任务失败: {exc}")
        return None


def _get_bound_task_id() -> str | None:
    return getattr(_TASK_CONTEXT, "task_id", None)


def _get_cancel_event(task_id: str) -> threading.Event:
    with _CANCEL_LOCK:
        return _CANCEL_EVENTS.setdefault(task_id, threading.Event())


def _reset_cancel_flag(task_id: str) -> None:
    _get_cancel_event(task_id).clear()


def _clear_cancel_flag(task_id: str | None) -> None:
    if not task_id:
        return
    with _CANCEL_LOCK:
        _CANCEL_EVENTS.pop(task_id, None)


def create_task(
    task_id: str,
    task_type: str,
    description: str = "",
) -> dict:
    now = datetime.now().isoformat()
    return {
        "task_id": task_id,
        "task_type": task_type,
        "description": description,
        "status": "pending",
        "progress": 0.0,
        "message": "等待执行",
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }


def save_task_state(task_state: dict) -> None:
    task_state["updated_at"] = datetime.now().isoformat()
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            payload = {
                "description": task_state.get("description", ""),
                "message": task_state.get("message", ""),
                "result": task_state.get("result"),
                "error": task_state.get("error"),
                "completed_at": task_state.get("completed_at"),
            }
            cursor.execute(
                """
                INSERT OR REPLACE INTO task_queue
                (task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_state["task_id"],
                    task_state["task_type"],
                    json.dumps(payload, ensure_ascii=False),
                    str(task_state["status"]).upper(),
                    task_state.get("progress", 0.0),
                    task_state.get("error", ""),
                    task_state.get("created_at"),
                    task_state["updated_at"],
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.error(f"保存任务状态失败: {exc}")


def load_task_state(
    task_types: str | Iterable[str] | None = None,
    *,
    active_only: bool = False,
) -> dict | None:
    try:
        where_clause, params = _build_filters(task_types, active_only=active_only)
        order_by = (
            "update_time DESC"
            if active_only
            else "CASE WHEN status IN ('PENDING', 'RUNNING') THEN 0 ELSE 1 END, update_time DESC"
        )
        query = f"""
            SELECT task_id, task_type, payload, status, progress, error_msg, create_time, update_time
            FROM task_queue
            {where_clause}
            ORDER BY {order_by}
            LIMIT 1
        """
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return _row_to_task(row) if row else None
    except Exception as exc:
        logger.error(f"读取任务状态失败: {exc}")
        return None


def _resolve_task_id(
    task_id: str | None = None,
    task_types: str | Iterable[str] | None = None,
    *,
    active_only: bool = False,
) -> str | None:
    if task_id:
        return task_id
    bound_task_id = _get_bound_task_id()
    if bound_task_id:
        return bound_task_id
    state = load_task_state(task_types=task_types, active_only=active_only)
    return state.get("task_id") if state else None


def update_task_progress(
    progress: float,
    message: str = "",
    status: str = "running",
    *,
    task_id: str | None = None,
) -> None:
    resolved_id = _resolve_task_id(task_id)
    if not resolved_id:
        return
    state = _load_task_by_id(resolved_id)
    if state is None:
        return
    state["progress"] = min(max(progress, 0.0), 1.0)
    state["status"] = status
    if message:
        state["message"] = message
    save_task_state(state)


def mark_task_success(
    result: Any = None,
    message: str = "任务完成",
    *,
    task_id: str | None = None,
) -> None:
    resolved_id = _resolve_task_id(task_id)
    if not resolved_id:
        return
    state = _load_task_by_id(resolved_id)
    if state is None:
        return
    state["status"] = "success"
    state["progress"] = 1.0
    state["message"] = message
    state["result"] = result
    state["completed_at"] = datetime.now().isoformat()
    save_task_state(state)


def mark_task_failed(error: str, *, task_id: str | None = None) -> None:
    resolved_id = _resolve_task_id(task_id)
    if not resolved_id:
        return
    state = _load_task_by_id(resolved_id)
    if state is None:
        return
    state["status"] = "failed"
    state["message"] = f"错误: {error}"
    state["error"] = error
    state["completed_at"] = datetime.now().isoformat()
    save_task_state(state)


def mark_task_cancelled(task_id: str | None = None, message: str = "任务已取消") -> None:
    resolved_id = _resolve_task_id(task_id, active_only=True)
    if not resolved_id:
        return
    state = _load_task_by_id(resolved_id)
    if state is None:
        return
    state["status"] = "cancelled"
    state["message"] = message
    state["error"] = message
    state["completed_at"] = datetime.now().isoformat()
    save_task_state(state)


def clear_task_state(
    *,
    task_id: str | None = None,
    task_types: str | Iterable[str] | None = None,
) -> None:
    resolved_id = _resolve_task_id(task_id, task_types=task_types)
    if not resolved_id:
        return
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM task_queue WHERE task_id = ?", (resolved_id,))
            conn.commit()
        _clear_cancel_flag(resolved_id)
    except Exception as exc:
        logger.error(f"清除任务状态失败: {exc}")


def cancel_task(
    *,
    task_id: str | None = None,
    task_types: str | Iterable[str] | None = None,
) -> None:
    resolved_id = _resolve_task_id(task_id, task_types=task_types, active_only=True)
    if not resolved_id:
        return
    _get_cancel_event(resolved_id).set()
    mark_task_cancelled(resolved_id)


def is_task_cancelled(*, task_id: str | None = None) -> bool:
    resolved_id = _resolve_task_id(task_id)
    if not resolved_id:
        return False
    return _get_cancel_event(resolved_id).is_set()


def run_task_in_background(
    task_func: Callable,
    task_id: str,
    task_type: str,
    description: str = "",
    success_message: str = "任务完成",
    *args,
    **kwargs,
) -> None:
    _reset_cancel_flag(task_id)
    initial_state = create_task(task_id, task_type, description)
    save_task_state(initial_state)

    def _worker():
        _TASK_CONTEXT.task_id = task_id
        try:
            update_task_progress(0.0, "任务开始执行", task_id=task_id)

            if is_task_cancelled(task_id=task_id):
                mark_task_cancelled(task_id, "任务已取消")
                return

            result = task_func(*args, **kwargs)
            current_state = _load_task_by_id(task_id)
            if current_state and current_state.get("status") in {"success", "failed", "cancelled"}:
                return

            if is_task_cancelled(task_id=task_id):
                mark_task_cancelled(task_id, "任务已取消")
                return

            mark_task_success(result, success_message, task_id=task_id)
        except Exception as exc:
            logger.exception("后台任务执行异常")
            current_state = _load_task_by_id(task_id)
            if current_state and current_state.get("status") in {"success", "failed", "cancelled"}:
                return

            if is_task_cancelled(task_id=task_id):
                mark_task_cancelled(task_id, "任务已取消")
            else:
                mark_task_failed(str(exc), task_id=task_id)
        finally:
            _TASK_CONTEXT.task_id = None

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def load_task_history(
    limit: int = 10,
    *,
    task_types: str | Iterable[str] | None = None,
) -> list[dict]:
    try:
        where_clause, params = _build_filters(task_types, active_only=False)
        query = f"""
            SELECT task_id, task_type, payload, status, progress, error_msg, create_time, update_time
            FROM task_queue
            {where_clause}
            ORDER BY update_time DESC
            LIMIT ?
        """
        params.append(limit)

        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [_row_to_task(row) for row in cursor.fetchall()]
    except Exception as exc:
        logger.error(f"加载任务历史失败: {exc}")
        return []
