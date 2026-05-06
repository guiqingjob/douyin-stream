"""领域实体 - 核心业务模型"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
import uuid


class AssetStatus(str, Enum):
    """素材状态"""
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    TRANSCRIBED = "transcribed"
    EXPORTED = "exported"
    FAILED = "failed"


class TranscriptStatus(str, Enum):
    """转写状态"""
    NONE = "none"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Asset:
    """素材实体"""
    asset_id: str
    creator_uid: str
    title: str
    video_path: Optional[Path] = None
    video_status: AssetStatus = AssetStatus.PENDING
    transcript_path: Optional[Path] = None
    transcript_status: TranscriptStatus = TranscriptStatus.NONE
    transcript_preview: Optional[str] = None
    source_platform: str = "douyin"
    source_url: Optional[str] = None
    is_read: bool = False
    is_starred: bool = False
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, creator_uid: str, title: str, **kwargs) -> "Asset":
        """创建素材实体"""
        return cls(
            asset_id=str(uuid.uuid4()),
            creator_uid=creator_uid,
            title=title,
            **kwargs
        )
    
    def mark_downloaded(self, video_path: Path) -> None:
        """标记为已下载"""
        self.video_path = video_path
        self.video_status = AssetStatus.DOWNLOADED
        self.update_time = datetime.now()
    
    def mark_transcribed(self, transcript_path: Path, preview: str) -> None:
        """标记为已转写"""
        self.transcript_path = transcript_path
        self.transcript_preview = preview
        self.transcript_status = TranscriptStatus.COMPLETED
        self.video_status = AssetStatus.TRANSCRIBED
        self.update_time = datetime.now()
    
    def mark_failed(self, error_type: str, error_message: str) -> None:
        """标记为失败"""
        self.video_status = AssetStatus.FAILED
        self.transcript_status = TranscriptStatus.FAILED
        self.update_time = datetime.now()
        self._error_type = error_type
        self._error_message = error_message


@dataclass
class Creator:
    """创作者实体"""
    uid: str
    nickname: str
    avatar_url: Optional[str] = None
    video_count: int = 0
    downloaded_count: int = 0
    transcript_count: int = 0
    last_fetch_time: Optional[datetime] = None
    status: str = "active"
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)
    
    def increment_downloaded(self) -> None:
        """增加下载计数"""
        self.downloaded_count += 1
        self.update_time = datetime.now()
    
    def increment_transcript(self) -> None:
        """增加转写计数"""
        self.transcript_count += 1
        self.update_time = datetime.now()


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型"""
    DOWNLOAD = "download"
    TRANSCRIBE = "transcribe"
    EXPORT = "export"
    PIPELINE = "pipeline"
    CLEANUP = "cleanup"


@dataclass
class Task:
    """任务实体"""
    task_id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any] = field(default_factory=dict)
    progress: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, task_type: TaskType, **kwargs) -> "Task":
        """创建任务实体"""
        return cls(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            **kwargs
        )
    
    def start(self) -> None:
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.updated_at = datetime.now()
    
    def complete(self) -> None:
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def fail(self, error_message: str) -> None:
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now()
    
    def cancel(self) -> None:
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.now()
    
    def update_progress(self, progress: Dict[str, Any]) -> None:
        """更新进度"""
        self.progress.update(progress)
        self.updated_at = datetime.now()


@dataclass
class Transcript:
    """转写实体"""
    transcript_id: str
    asset_id: str
    content: str
    duration: int = 0
    word_count: int = 0
    confidence: float = 0.0
    create_time: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, asset_id: str, content: str) -> "Transcript":
        """创建转写实体"""
        return cls(
            transcript_id=str(uuid.uuid4()),
            asset_id=asset_id,
            content=content,
            word_count=len(content),
        )
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        return f"# 转写内容\n\n{self.content}"