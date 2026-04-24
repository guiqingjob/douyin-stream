"""全局任务取消注册表，供 Douyin 下载器与 API 路由共享。"""
from __future__ import annotations

import threading

_cancel_events: dict[str, threading.Event] = {}

# 下载进度追踪（供 API 轮询使用）
_download_progress: dict[str, dict] = {}


def set_cancel_event(task_id: str) -> None:
    """标记指定任务为已取消。"""
    _cancel_events[task_id] = threading.Event()
    _cancel_events[task_id].set()


def clear_cancel_event(task_id: str) -> None:
    """清理指定任务的取消标志。"""
    _cancel_events.pop(task_id, None)


def is_task_cancelled(task_id: str | None) -> bool:
    """检查指定任务是否已被请求取消。"""
    if not task_id:
        return False
    event = _cancel_events.get(task_id)
    return event is not None and event.is_set()


def get_download_progress(task_id: str) -> dict | None:
    """获取指定任务的下载进度信息。"""
    return _download_progress.get(task_id)


def set_download_progress(task_id: str, info: dict) -> None:
    """设置指定任务的下载进度信息。"""
    _download_progress[task_id] = info


def clear_download_progress(task_id: str) -> None:
    """清理指定任务的下载进度信息。"""
    _download_progress.pop(task_id, None)
