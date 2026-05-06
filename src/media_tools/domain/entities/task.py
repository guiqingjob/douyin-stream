from __future__ import annotations
"""Task 领域实体 - 任务管理模型"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIAL_FAILED = "PARTIAL_FAILED"


class TaskType(Enum):
    DOWNLOAD = "download"
    TRANSCRIBE = "transcribe"
    PIPELINE = "pipeline"
    SYNC = "sync"
    CLEANUP = "cleanup"


class Stage(str, Enum):
    """任务阶段枚举"""
    CREATED = "created"
    FETCHING = "fetching"
    AUDITING = "auditing"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def from_string(cls, value: str) -> "Stage":
        """从字符串转换为 Stage 枚举"""
        value = value.strip().lower()
        mapping = {
            "initializing": cls.FETCHING,
            "scanning": cls.FETCHING,
            "queued": cls.CREATED,
            "listing": cls.FETCHING,
            "fetching": cls.FETCHING,
            "auditing": cls.AUDITING,
            "reconcile": cls.AUDITING,
            "downloading": cls.DOWNLOADING,
            "download": cls.DOWNLOADING,
            "transcribing": cls.TRANSCRIBING,
            "transcribe": cls.TRANSCRIBING,
            "exporting": cls.EXPORTING,
            "export": cls.EXPORTING,
            "completed": cls.COMPLETED,
            "success": cls.COMPLETED,
            "done": cls.COMPLETED,
            "failed": cls.FAILED,
            "error": cls.FAILED,
            "cancelled": cls.CANCELLED,
            "canceled": cls.CANCELLED,
        }
        return mapping.get(value, cls.DOWNLOADING)


@dataclass
class DownloadProgress:
    """下载阶段进度"""
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    total: int = 0
    current_video: str = ""
    current_index: int = 0

    def to_dict(self) -> dict:
        return {
            "downloaded": self.downloaded,
            "skipped": self.skipped,
            "failed": self.failed,
            "total": self.total,
            "current_video": self.current_video,
            "current_index": self.current_index,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["DownloadProgress"]:
        if not data:
            return None
        return cls(
            downloaded=int(data.get("downloaded", 0)),
            skipped=int(data.get("skipped", 0)),
            failed=int(data.get("failed", 0)),
            total=int(data.get("total", 0)),
            current_video=str(data.get("current_video", "")),
            current_index=int(data.get("current_index", 0)),
        )


@dataclass
class TranscribeProgress:
    """转写阶段进度"""
    done: int = 0
    skipped: int = 0
    failed: int = 0
    total: int = 0
    current_video: str = ""
    current_account: str = ""

    def to_dict(self) -> dict:
        return {
            "done": self.done,
            "skipped": self.skipped,
            "failed": self.failed,
            "total": self.total,
            "current_video": self.current_video,
            "current_account": self.current_account,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["TranscribeProgress"]:
        if not data:
            return None
        return cls(
            done=int(data.get("done", 0)),
            skipped=int(data.get("skipped", 0)),
            failed=int(data.get("failed", 0)),
            total=int(data.get("total", 0)),
            current_video=str(data.get("current_video", "")),
            current_account=str(data.get("current_account", "")),
        )


@dataclass
class TaskProgress:
    """完整任务进度"""
    stage: Stage = Stage.CREATED
    overall_percent: float = 0.0
    download_progress: Optional[DownloadProgress] = None
    transcribe_progress: Optional[TranscribeProgress] = None
    error_count: int = 0
    errors: list = field(default_factory=list)
    start_time: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "overall_percent": self.overall_percent,
            "download_progress": self.download_progress.to_dict() if self.download_progress else None,
            "transcribe_progress": self.transcribe_progress.to_dict() if self.transcribe_progress else None,
            "error_count": self.error_count,
            "errors": self.errors,
            "start_time": self.start_time,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["TaskProgress"]:
        if not data:
            return None
        stage_str = data.get("stage", "created")
        try:
            stage = Stage(stage_str)
        except ValueError:
            stage = Stage.from_string(stage_str)
        return cls(
            stage=stage,
            overall_percent=float(data.get("overall_percent", 0.0)),
            download_progress=DownloadProgress.from_dict(data.get("download_progress")),
            transcribe_progress=TranscribeProgress.from_dict(data.get("transcribe_progress")),
            error_count=int(data.get("error_count", 0)),
            errors=list(data.get("errors", [])),
            start_time=data.get("start_time"),
        )


class Task:
    """任务实体 - 任务管理模型"""

    def __init__(
        self,
        task_id: str,
        task_type: TaskType,
        status: TaskStatus = TaskStatus.PENDING,
        progress: float = 0.0,
        payload: Optional[dict] = None,
        error_msg: Optional[str] = None,
        create_time: Optional[datetime] = None,
        update_time: Optional[datetime] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        cancel_requested: bool = False,
        auto_retry: bool = False,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.status = status
        self.progress = progress
        self.payload = payload or {}
        self.error_msg = error_msg
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()
        self.start_time = start_time
        self.end_time = end_time
        self.cancel_requested = cancel_requested
        self.auto_retry = auto_retry

    def start(self) -> None:
        """标记任务开始"""
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"Cannot start task from state {self.status.value}")
        self.status = TaskStatus.RUNNING
        self.progress = 0.0
        self.start_time = datetime.now()
        self.update_time = datetime.now()

    def complete(self) -> None:
        """标记任务完成"""
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("Task is already completed")
        self.status = TaskStatus.COMPLETED
        self.progress = 1.0
        self.end_time = datetime.now()
        self.update_time = datetime.now()

    def fail(self, error_msg: str) -> None:
        """标记任务失败"""
        if self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise ValueError(f"Cannot fail task from terminal state {self.status.value}")
        self.status = TaskStatus.FAILED
        self.error_msg = error_msg[:2000] if error_msg else None
        self.end_time = datetime.now()
        self.update_time = datetime.now()

    def cancel(self) -> None:
        """取消任务"""
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            raise ValueError(f"Cannot cancel task from state {self.status.value}")
        self.status = TaskStatus.CANCELLED
        self.end_time = datetime.now()
        self.update_time = datetime.now()

    def mark_partial_failed(self) -> None:
        """标记部分失败"""
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            raise ValueError(f"Cannot mark partial failed from state {self.status.value}")
        self.status = TaskStatus.PARTIAL_FAILED
        self.end_time = datetime.now()
        self.update_time = datetime.now()

    def update_progress(self, progress: float, msg: str) -> None:
        """更新任务进度"""
        if self.is_terminal():
            raise ValueError(f"Cannot update progress on terminal task")
        self.progress = max(0.0, min(1.0, progress))
        self.payload["msg"] = msg
        self.update_time = datetime.now()

    def update_payload(self, key: str, value: Any) -> None:
        """更新 payload 字段"""
        self.payload[key] = value
        self.update_time = datetime.now()

    def patch_payload(self, patch: dict[str, Any]) -> None:
        """批量更新 payload"""
        self.payload.update(patch)
        self.update_time = datetime.now()

    def request_cancel(self) -> None:
        """请求取消任务"""
        self.cancel_requested = True
        self.update_time = datetime.now()

    def is_terminal(self) -> bool:
        """判断是否为终态"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def is_active(self) -> bool:
        """判断是否为活跃状态"""
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        import json

        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "payload": json.dumps(self.payload, ensure_ascii=False),
            "error_msg": self.error_msg,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "cancel_requested": self.cancel_requested,
            "auto_retry": self.auto_retry,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """从字典创建 Task 实例"""
        import json

        payload = {}
        if data.get("payload"):
            try:
                payload = json.loads(data["payload"])
                if not isinstance(payload, dict):
                    payload = {}
            except (json.JSONDecodeError, TypeError):
                payload = {}

        return cls(
            task_id=data["task_id"],
            task_type=TaskType(data.get("task_type", "pipeline")),
            status=TaskStatus(data.get("status", "PENDING")),
            progress=data.get("progress", 0.0),
            payload=payload,
            error_msg=data.get("error_msg"),
            create_time=datetime.fromisoformat(data["create_time"]) if data.get("create_time") else None,
            update_time=datetime.fromisoformat(data["update_time"]) if data.get("update_time") else None,
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            cancel_requested=data.get("cancel_requested", False),
            auto_retry=data.get("auto_retry", False),
        )
