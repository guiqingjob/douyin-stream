"""任务状态机 — 定义所有合法的状态转移和阶段划分。"""
from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable


class TaskStatus(Enum):
    """任务状态"""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskStage(Enum):
    """任务阶段（用于前端展示进度）"""
    INITIALIZING = "initializing"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


# 合法状态转移图
VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.PENDING: [TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED],
    TaskStatus.RUNNING: [TaskStatus.PAUSED, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
    TaskStatus.PAUSED: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
    TaskStatus.COMPLETED: [],
    TaskStatus.FAILED: [TaskStatus.RUNNING],  # 重试
    TaskStatus.CANCELLED: [TaskStatus.RUNNING],  # 重试
}


class InvalidTransitionError(ValueError):
    """非法状态转移异常"""
    pass


def validate_transition(from_status: TaskStatus, to_status: TaskStatus) -> None:
    """验证状态转移是否合法，不合法则抛出 InvalidTransitionError。"""
    allowed = VALID_TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        raise InvalidTransitionError(
            f"Invalid transition: {from_status.name} -> {to_status.name}"
        )


def validate_transition_by_str(from_status_str: str, to_status_str: str) -> None:
    """字符串版本的状态转移验证。"""
    try:
        from_s = TaskStatus[from_status_str.upper()]
        to_s = TaskStatus[to_status_str.upper()]
    except KeyError as e:
        raise InvalidTransitionError(f"Unknown status: {e}") from e
    validate_transition(from_s, to_s)


@dataclass
class Subtask:
    """子任务"""
    id: str
    title: str
    status: TaskStatus
    error: str | None = None
    progress: float = 0.0


@dataclass
class TaskResult:
    """任务执行结果"""
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_count: int = 0
    subtasks: list[Subtask] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success_count,
            "failed": self.failed_count,
            "skipped": self.skipped_count,
            "total": self.total_count,
        }
