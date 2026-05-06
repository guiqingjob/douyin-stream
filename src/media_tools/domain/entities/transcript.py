from __future__ import annotations
"""Transcript 领域实体 - 转写信息模型"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class TranscriptFormat(Enum):
    MARKDOWN = "md"
    DOCX = "docx"
    TXT = "txt"


class Transcript:
    """转写实体 - 转写信息模型"""

    def __init__(
        self,
        transcript_id: str,
        asset_id: str,
        text: str,
        format: TranscriptFormat = TranscriptFormat.MARKDOWN,
        path: Optional[Path] = None,
        preview: Optional[str] = None,
        word_count: int = 0,
        char_count: int = 0,
        create_time: Optional[datetime] = None,
        update_time: Optional[datetime] = None,
    ):
        self.transcript_id = transcript_id
        self.asset_id = asset_id
        self.text = text
        self.format = format
        self.path = path
        self.preview = preview
        self.word_count = word_count
        self.char_count = char_count
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def update_text(self, text: str) -> None:
        """更新转写文本"""
        self.text = text
        self.word_count = len(text.split())
        self.char_count = len(text)
        self.update_time = datetime.now()

    def generate_preview(self, max_length: int = 200) -> None:
        """生成预览文本"""
        if self.text:
            self.preview = self.text[:max_length] + ("..." if len(self.text) > max_length else "")
        self.update_time = datetime.now()

    def update_path(self, path: Path) -> None:
        """更新文件路径"""
        self.path = path
        self.update_time = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "transcript_id": self.transcript_id,
            "asset_id": self.asset_id,
            "text": self.text,
            "format": self.format.value,
            "path": str(self.path) if self.path else None,
            "preview": self.preview,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transcript":
        """从字典创建 Transcript 实例"""
        return cls(
            transcript_id=data["transcript_id"],
            asset_id=data["asset_id"],
            text=data.get("text", ""),
            format=TranscriptFormat(data.get("format", "md")),
            path=Path(data["path"]) if data.get("path") else None,
            preview=data.get("preview"),
            word_count=data.get("word_count", 0),
            char_count=data.get("char_count", 0),
            create_time=datetime.fromisoformat(data["create_time"]) if data.get("create_time") else None,
            update_time=datetime.fromisoformat(data["update_time"]) if data.get("update_time") else None,
        )