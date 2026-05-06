from __future__ import annotations
"""Creator 领域实体 - 创作者信息模型"""

from datetime import datetime
from enum import Enum
from typing import Optional


class PlatformType(Enum):
    DOUYIN = "douyin"
    BILIBILI = "bilibili"


class SyncStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SYNCING = "syncing"


class Creator:
    """创作者实体 - 创作者信息模型"""

    def __init__(
        self,
        uid: str,
        sec_user_id: str,
        nickname: str,
        platform: PlatformType = PlatformType.DOUYIN,
        sync_status: SyncStatus = SyncStatus.ACTIVE,
        homepage_url: Optional[str] = None,
        avatar: Optional[str] = None,
        bio: Optional[str] = None,
        last_fetch_time: Optional[datetime] = None,
        downloaded_count: int = 0,
        transcript_count: int = 0,
    ):
        self.uid = uid
        self.sec_user_id = sec_user_id
        self.nickname = nickname
        self.platform = platform
        self.sync_status = sync_status
        self.homepage_url = homepage_url
        self.avatar = avatar
        self.bio = bio
        self.last_fetch_time = last_fetch_time
        self.downloaded_count = downloaded_count
        self.transcript_count = transcript_count

    def increment_downloaded(self) -> None:
        """增加下载计数"""
        self.downloaded_count += 1

    def increment_transcript(self) -> None:
        """增加转写计数"""
        self.transcript_count += 1

    def update_last_fetch_time(self) -> None:
        """更新上次同步时间"""
        self.last_fetch_time = datetime.now()

    def activate(self) -> None:
        """激活创作者"""
        self.sync_status = SyncStatus.ACTIVE

    def deactivate(self) -> None:
        """停用创作者"""
        self.sync_status = SyncStatus.INACTIVE

    def mark_syncing(self) -> None:
        """标记正在同步"""
        self.sync_status = SyncStatus.SYNCING

    def update_info(
        self,
        nickname: Optional[str] = None,
        homepage_url: Optional[str] = None,
        avatar: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> None:
        """更新创作者信息"""
        if nickname is not None:
            self.nickname = nickname
        if homepage_url is not None:
            self.homepage_url = homepage_url
        if avatar is not None:
            self.avatar = avatar
        if bio is not None:
            self.bio = bio

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "uid": self.uid,
            "sec_user_id": self.sec_user_id,
            "nickname": self.nickname,
            "platform": self.platform.value,
            "sync_status": self.sync_status.value,
            "homepage_url": self.homepage_url,
            "avatar": self.avatar,
            "bio": self.bio,
            "last_fetch_time": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            "downloaded_count": self.downloaded_count,
            "transcript_count": self.transcript_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Creator":
        """从字典创建 Creator 实例"""
        return cls(
            uid=data["uid"],
            sec_user_id=data.get("sec_user_id", ""),
            nickname=data.get("nickname", ""),
            platform=PlatformType(data.get("platform", "douyin")),
            sync_status=SyncStatus(data.get("sync_status", "active")),
            homepage_url=data.get("homepage_url"),
            avatar=data.get("avatar"),
            bio=data.get("bio"),
            last_fetch_time=datetime.fromisoformat(data["last_fetch_time"]) if data.get("last_fetch_time") else None,
            downloaded_count=data.get("downloaded_count", 0),
            transcript_count=data.get("transcript_count", 0),
        )