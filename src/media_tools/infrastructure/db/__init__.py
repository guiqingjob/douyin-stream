"""基础设施层 - 数据库实现"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from media_tools.db.core import get_db_connection
from media_tools.domain.entities import Asset, AssetStatus, Creator, Task, TaskStatus, TaskType, Transcript, TranscriptStatus
from media_tools.domain.repositories import (
    AssetRepository,
    CreatorRepository,
    TaskRepository,
    TranscriptRepository,
)


class SQLiteAssetRepository(AssetRepository):
    """SQLite 素材仓储实现"""
    
    def save(self, asset: Asset) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO media_assets
                (asset_id, creator_uid, title, video_path, video_status,
                 transcript_path, transcript_status, transcript_preview,
                 source_platform, source_url, is_read, is_starred,
                 create_time, update_time)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    asset.asset_id,
                    asset.creator_uid,
                    asset.title,
                    str(asset.video_path) if asset.video_path else None,
                    asset.video_status.value,
                    str(asset.transcript_path) if asset.transcript_path else None,
                    asset.transcript_status.value,
                    asset.transcript_preview,
                    asset.source_platform,
                    asset.source_url,
                    asset.is_read,
                    asset.is_starred,
                    asset.create_time.isoformat(),
                    asset.update_time.isoformat(),
                )
            )
            conn.commit()
    
    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM media_assets WHERE asset_id = ?",
                (asset_id,)
            ).fetchone()
            if row:
                return self._row_to_asset(row)
        return None
    
    def find_by_creator(self, creator_uid: str) -> List[Asset]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM media_assets WHERE creator_uid = ? ORDER BY update_time DESC",
                (creator_uid,)
            ).fetchall()
            return [self._row_to_asset(row) for row in rows]
    
    def find_all(self) -> List[Asset]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM media_assets ORDER BY update_time DESC"
            ).fetchall()
            return [self._row_to_asset(row) for row in rows]
    
    def delete(self, asset_id: str) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
            conn.commit()
    
    def update(self, asset: Asset) -> None:
        self.save(asset)
    
    def count_by_status(self, status: str) -> int:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM media_assets WHERE video_status = ?",
                (status,)
            ).fetchone()
            return row[0] if row else 0
    
    @staticmethod
    def _row_to_asset(row: sqlite3.Row) -> Asset:
        """将数据库行转换为 Asset 实体"""
        return Asset(
            asset_id=row["asset_id"],
            creator_uid=row["creator_uid"],
            title=row["title"],
            video_path=Path(row["video_path"]) if row["video_path"] else None,
            video_status=AssetStatus(row["video_status"]) if row["video_status"] else AssetStatus.PENDING,
            transcript_path=Path(row["transcript_path"]) if row["transcript_path"] else None,
            transcript_status=TranscriptStatus(row["transcript_status"]) if row["transcript_status"] else TranscriptStatus.NONE,
            transcript_preview=row["transcript_preview"],
            source_platform=row["source_platform"] or "douyin",
            source_url=row["source_url"],
            is_read=bool(row["is_read"]),
            is_starred=bool(row["is_starred"]),
            create_time=datetime.fromisoformat(row["create_time"]) if row["create_time"] else datetime.now(),
            update_time=datetime.fromisoformat(row["update_time"]) if row["update_time"] else datetime.now(),
        )


class SQLiteCreatorRepository(CreatorRepository):
    """SQLite 创作者仓储实现"""
    
    def save(self, creator: Creator) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO creators
                (uid, nickname, avatar_url, video_count, downloaded_count,
                 transcript_count, last_fetch_time, status, create_time, update_time)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    creator.uid,
                    creator.nickname,
                    creator.avatar_url,
                    creator.video_count,
                    creator.downloaded_count,
                    creator.transcript_count,
                    creator.last_fetch_time.isoformat() if creator.last_fetch_time else None,
                    creator.status,
                    creator.create_time.isoformat(),
                    creator.update_time.isoformat(),
                )
            )
            conn.commit()
    
    def find_by_id(self, uid: str) -> Optional[Creator]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM creators WHERE uid = ?",
                (uid,)
            ).fetchone()
            if row:
                return self._row_to_creator(row)
        return None
    
    def find_all(self) -> List[Creator]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM creators ORDER BY nickname ASC"
            ).fetchall()
            return [self._row_to_creator(row) for row in rows]
    
    def delete(self, uid: str) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM creators WHERE uid = ?", (uid,))
            conn.commit()
    
    def update(self, creator: Creator) -> None:
        self.save(creator)
    
    @staticmethod
    def _row_to_creator(row: sqlite3.Row) -> Creator:
        """将数据库行转换为 Creator 实体"""
        return Creator(
            uid=row["uid"],
            nickname=row["nickname"],
            avatar_url=row["avatar_url"],
            video_count=row["video_count"] or 0,
            downloaded_count=row["downloaded_count"] or 0,
            transcript_count=row["transcript_count"] or 0,
            last_fetch_time=datetime.fromisoformat(row["last_fetch_time"]) if row["last_fetch_time"] else None,
            status=row["status"] or "active",
            create_time=datetime.fromisoformat(row["create_time"]) if row["create_time"] else datetime.now(),
            update_time=datetime.fromisoformat(row["update_time"]) if row["update_time"] else datetime.now(),
        )


class SQLiteTaskRepository(TaskRepository):
    """SQLite 任务仓储实现"""
    
    def save(self, task: Task) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO tasks
                (task_id, task_type, status, payload, progress, error_message,
                 created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id,
                    task.task_type.value,
                    task.status.value,
                    json.dumps(task.payload),
                    json.dumps(task.progress),
                    task.error_message,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                )
            )
            conn.commit()
    
    def find_by_id(self, task_id: str) -> Optional[Task]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,)
            ).fetchone()
            if row:
                return self._row_to_task(row)
        return None
    
    def find_active(self) -> List[Task]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status IN ('pending', 'running') ORDER BY created_at DESC"
            ).fetchall()
            return [self._row_to_task(row) for row in rows]
    
    def find_all(self) -> List[Task]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC"
            ).fetchall()
            return [self._row_to_task(row) for row in rows]
    
    def update(self, task: Task) -> None:
        self.save(task)
    
    def delete(self, task_id: str) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
    
    def clear_history(self) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE status IN ('completed', 'failed', 'cancelled')")
            conn.commit()
    
    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        """将数据库行转换为 Task 实体"""
        return Task(
            task_id=row["task_id"],
            task_type=TaskType(row["task_type"]),
            status=TaskStatus(row["status"]),
            payload=json.loads(row["payload"]) if row["payload"] else {},
            progress=json.loads(row["progress"]) if row["progress"] else {},
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )


class SQLiteTranscriptRepository(TranscriptRepository):
    """SQLite 转写仓储实现"""
    
    def save(self, transcript: Transcript) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO transcripts
                (transcript_id, asset_id, content, duration, word_count, confidence, create_time)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    transcript.transcript_id,
                    transcript.asset_id,
                    transcript.content,
                    transcript.duration,
                    transcript.word_count,
                    transcript.confidence,
                    transcript.create_time.isoformat(),
                )
            )
            conn.commit()
    
    def find_by_id(self, transcript_id: str) -> Optional[Transcript]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM transcripts WHERE transcript_id = ?",
                (transcript_id,)
            ).fetchone()
            if row:
                return self._row_to_transcript(row)
        return None
    
    def find_by_asset(self, asset_id: str) -> Optional[Transcript]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM transcripts WHERE asset_id = ?",
                (asset_id,)
            ).fetchone()
            if row:
                return self._row_to_transcript(row)
        return None
    
    def delete(self, transcript_id: str) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM transcripts WHERE transcript_id = ?", (transcript_id,))
            conn.commit()
    
    @staticmethod
    def _row_to_transcript(row: sqlite3.Row) -> Transcript:
        """将数据库行转换为 Transcript 实体"""
        return Transcript(
            transcript_id=row["transcript_id"],
            asset_id=row["asset_id"],
            content=row["content"],
            duration=row["duration"] or 0,
            word_count=row["word_count"] or 0,
            confidence=row["confidence"] or 0.0,
            create_time=datetime.fromisoformat(row["create_time"]) if row["create_time"] else datetime.now(),
        )


# 工厂函数
def create_asset_repository() -> AssetRepository:
    return SQLiteAssetRepository()

def create_creator_repository() -> CreatorRepository:
    return SQLiteCreatorRepository()

def create_task_repository() -> TaskRepository:
    return SQLiteTaskRepository()

def create_transcript_repository() -> TranscriptRepository:
    return SQLiteTranscriptRepository()