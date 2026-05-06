from __future__ import annotations
"""Asset 领域实体 - 素材核心业务模型"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class VideoStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    FAILED = "failed"


class TranscriptStatus(Enum):
    NONE = "none"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"


class Asset:
    """素材实体 - 核心业务模型"""

    def __init__(
        self,
        asset_id: str,
        creator_uid: str,
        title: str,
        video_path: Optional[Path] = None,
        video_status: VideoStatus = VideoStatus.PENDING,
        transcript_path: Optional[Path] = None,
        transcript_status: TranscriptStatus = TranscriptStatus.NONE,
        transcript_preview: Optional[str] = None,
        transcript_text: Optional[str] = None,
        source_url: Optional[str] = None,
        source_platform: Optional[str] = None,
        duration: Optional[int] = None,
        folder_path: Optional[str] = None,
        is_read: bool = False,
        is_starred: bool = False,
        transcript_last_error: Optional[str] = None,
        transcript_error_type: Optional[str] = None,
        transcript_retry_count: int = 0,
        transcript_failed_at: Optional[datetime] = None,
        last_task_id: Optional[str] = None,
        create_time: Optional[datetime] = None,
        update_time: Optional[datetime] = None,
    ):
        self.asset_id = asset_id
        self.creator_uid = creator_uid
        self.title = title
        self.video_path = video_path
        self.video_status = video_status
        self.transcript_path = transcript_path
        self.transcript_status = transcript_status
        self.transcript_preview = transcript_preview
        self.transcript_text = transcript_text
        self.source_url = source_url
        self.source_platform = source_platform
        self.duration = duration
        self.folder_path = folder_path
        self.is_read = is_read
        self.is_starred = is_starred
        self.transcript_last_error = transcript_last_error
        self.transcript_error_type = transcript_error_type
        self.transcript_retry_count = transcript_retry_count
        self.transcript_failed_at = transcript_failed_at
        self.last_task_id = last_task_id
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def mark_downloaded(self, video_path: Path) -> None:
        """标记下载完成"""
        if not video_path or not isinstance(video_path, Path):
            raise ValueError("video_path must be a valid Path")
        self.video_path = video_path
        self.video_status = VideoStatus.DOWNLOADED
        self.update_time = datetime.now()

    def mark_downloading(self) -> None:
        """标记正在下载"""
        if self.video_status not in (VideoStatus.PENDING, VideoStatus.FAILED):
            raise ValueError(f"Cannot start downloading from state {self.video_status.value}")
        self.video_status = VideoStatus.DOWNLOADING
        self.update_time = datetime.now()

    def mark_download_failed(self) -> None:
        """标记下载失败"""
        if self.video_status not in (VideoStatus.PENDING, VideoStatus.DOWNLOADING):
            raise ValueError(f"Cannot mark download failed from state {self.video_status.value}")
        self.video_status = VideoStatus.FAILED
        self.update_time = datetime.now()

    def mark_transcribed(
        self,
        transcript_path: Path,
        transcript_text: str,
        preview: Optional[str] = None,
    ) -> None:
        """标记转写完成"""
        if not transcript_path or not isinstance(transcript_path, Path):
            raise ValueError("transcript_path must be a valid Path")
        if not transcript_text:
            raise ValueError("transcript_text cannot be empty")
        self.transcript_path = transcript_path
        self.transcript_status = TranscriptStatus.COMPLETED
        self.transcript_text = transcript_text
        self.transcript_preview = preview
        self.transcript_last_error = None
        self.transcript_error_type = None
        self.transcript_retry_count = 0
        self.transcript_failed_at = None
        self.update_time = datetime.now()

    def mark_transcribing(self) -> None:
        """标记正在转写"""
        if self.transcript_status not in (TranscriptStatus.NONE, TranscriptStatus.FAILED):
            raise ValueError(f"Cannot start transcribing from state {self.transcript_status.value}")
        self.transcript_status = TranscriptStatus.TRANSCRIBING
        self.update_time = datetime.now()

    def mark_transcribe_failed(
        self, error_type: str, error_message: str
    ) -> None:
        """标记转写失败"""
        if self.transcript_status not in (TranscriptStatus.TRANSCRIBING, TranscriptStatus.NONE):
            raise ValueError(f"Cannot mark transcribe failed from state {self.transcript_status.value}")
        self.transcript_status = TranscriptStatus.FAILED
        self.transcript_last_error = error_message[:2000] if error_message else None
        self.transcript_error_type = error_type
        self.transcript_retry_count += 1
        self.transcript_failed_at = datetime.now()
        self.update_time = datetime.now()

    def reset_transcribe_status(self) -> None:
        """重置转写状态"""
        self.transcript_status = TranscriptStatus.NONE
        self.transcript_last_error = None
        self.transcript_error_type = None
        self.transcript_retry_count = 0
        self.transcript_failed_at = None
        self.update_time = datetime.now()

    def mark_read(self, is_read: bool) -> None:
        """标记已读状态"""
        self.is_read = is_read
        self.update_time = datetime.now()

    def toggle_starred(self) -> bool:
        """切换收藏状态"""
        self.is_starred = not self.is_starred
        self.update_time = datetime.now()
        return self.is_starred

    def update_title(self, title: str) -> None:
        """更新标题"""
        self.title = title
        self.update_time = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "asset_id": self.asset_id,
            "creator_uid": self.creator_uid,
            "title": self.title,
            "video_path": str(self.video_path) if self.video_path else None,
            "video_status": self.video_status.value,
            "transcript_path": str(self.transcript_path) if self.transcript_path else None,
            "transcript_status": self.transcript_status.value,
            "transcript_preview": self.transcript_preview,
            "transcript_text": self.transcript_text,
            "source_url": self.source_url,
            "source_platform": self.source_platform,
            "duration": self.duration,
            "folder_path": self.folder_path,
            "is_read": self.is_read,
            "is_starred": self.is_starred,
            "transcript_last_error": self.transcript_last_error,
            "transcript_error_type": self.transcript_error_type,
            "transcript_retry_count": self.transcript_retry_count,
            "transcript_failed_at": self.transcript_failed_at.isoformat() if self.transcript_failed_at else None,
            "last_task_id": self.last_task_id,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Asset":
        """从字典创建 Asset 实例"""
        return cls(
            asset_id=data["asset_id"],
            creator_uid=data["creator_uid"],
            title=data.get("title", ""),
            video_path=Path(data["video_path"]) if data.get("video_path") else None,
            video_status=VideoStatus(data.get("video_status", "pending")),
            transcript_path=Path(data["transcript_path"]) if data.get("transcript_path") else None,
            transcript_status=TranscriptStatus(data.get("transcript_status", "none")),
            transcript_preview=data.get("transcript_preview"),
            transcript_text=data.get("transcript_text"),
            source_url=data.get("source_url"),
            source_platform=data.get("source_platform"),
            duration=data.get("duration"),
            folder_path=data.get("folder_path"),
            is_read=data.get("is_read", False),
            is_starred=data.get("is_starred", False),
            transcript_last_error=data.get("transcript_last_error"),
            transcript_error_type=data.get("transcript_error_type"),
            transcript_retry_count=data.get("transcript_retry_count", 0),
            transcript_failed_at=datetime.fromisoformat(data["transcript_failed_at"]) if data.get("transcript_failed_at") else None,
            last_task_id=data.get("last_task_id"),
            create_time=datetime.fromisoformat(data["create_time"]) if data.get("create_time") else None,
            update_time=datetime.fromisoformat(data["update_time"]) if data.get("update_time") else None,
        )