"""全局任务取消注册表，供 Douyin 下载器与 API 路由共享。"""
from __future__ import annotations

import threading
import time

_cancel_events: dict[str, threading.Event] = {}

# 下载进度追踪（供 API 轮询使用）
_download_progress: dict[str, dict] = {}

# TTL 清理：超过此时间未清理的条目将被自动移除（秒）
_ENTRY_TTL = 3600  # 1 小时
_last_activity: dict[str, float] = {}

# 串行化跨线程访问，避免 _maybe_cleanup 在迭代时被并发写入触发 RuntimeError
_lock = threading.Lock()


def _maybe_cleanup() -> None:
    """惰性清理过期条目，防止内存泄漏。调用方需持有 _lock。"""
    now = time.monotonic()
    expired = [k for k, ts in _last_activity.items() if now - ts > _ENTRY_TTL]
    for k in expired:
        _cancel_events.pop(k, None)
        _download_progress.pop(k, None)
        _last_activity.pop(k, None)


def set_cancel_event(task_id: str) -> None:
    """标记指定任务为已取消。"""
    with _lock:
        event = threading.Event()
        event.set()
        _cancel_events[task_id] = event
        _last_activity[task_id] = time.monotonic()


def clear_cancel_event(task_id: str) -> None:
    """清理指定任务的取消标志。"""
    with _lock:
        _cancel_events.pop(task_id, None)
        _download_progress.pop(task_id, None)
        _last_activity.pop(task_id, None)


def is_task_cancelled(task_id: str | None) -> bool:
    """检查指定任务是否已被请求取消。"""
    if not task_id:
        return False
    with _lock:
        event = _cancel_events.get(task_id)
    return event is not None and event.is_set()


def get_download_progress(task_id: str) -> dict | None:
    """获取指定任务的下载进度信息。"""
    with _lock:
        return _download_progress.get(task_id)


def set_download_progress(task_id: str, info: dict) -> None:
    """设置指定任务的下载进度信息。"""
    with _lock:
        _download_progress[task_id] = info
        _last_activity[task_id] = time.monotonic()
        # 每 100 次设置时清理一次过期条目
        if len(_last_activity) % 100 == 0:
            _maybe_cleanup()


def clear_download_progress(task_id: str) -> None:
    """清理指定任务的下载进度信息。"""
    with _lock:
        _download_progress.pop(task_id, None)
        _last_activity.pop(task_id, None)
