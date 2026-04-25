"""事件总线 — 发布-订阅模式，用于解耦任务状态变更和通知。"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC
from dataclasses import dataclass
from typing import Callable, Awaitable, Any

logger = logging.getLogger(__name__)


@dataclass
class Event(ABC):
    """事件基类"""
    task_id: str
    timestamp: float


@dataclass
class TaskProgressEvent(Event):
    """任务进度事件"""
    stage: str
    percent: float
    message: str
    result_summary: dict | None = None
    subtasks: list[dict] | None = None


@dataclass
class TaskCompletedEvent(Event):
    """任务完成事件"""
    result_summary: dict | None = None
    subtasks: list[dict] | None = None


@dataclass
class TaskFailedEvent(Event):
    """任务失败事件"""
    error: str


Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """事件总线 — 支持多订阅者，异常隔离。"""

    def __init__(self):
        self._handlers: dict[type[Event], list[Handler]] = {}

    def subscribe(self, event_type: type[Event], handler: Handler) -> None:
        """订阅事件。"""
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: type[Event], handler: Handler) -> None:
        """取消订阅。"""
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    async def publish(self, event: Event) -> None:
        """发布事件 — 所有订阅者并行执行，异常不传播。"""
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return

        async def _safe_call(handler: Handler) -> None:
            try:
                await handler(event)
            except (RuntimeError, TypeError, ValueError):
                logger.exception(f"Event handler failed for {type(event).__name__}")

        await asyncio.gather(*[_safe_call(h) for h in handlers], return_exceptions=True)


# 全局事件总线实例
_global_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取全局事件总线。"""
    return _global_event_bus
