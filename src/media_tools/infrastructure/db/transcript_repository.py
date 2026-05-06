"""SQLite TranscriptRepository 实现"""
import logging
from typing import List, Optional

from media_tools.db.core import get_db_connection
from media_tools.domain.entities.transcript import Transcript, TranscriptFormat
from media_tools.domain.repositories.transcript_repository import TranscriptRepository

logger = logging.getLogger(__name__)


class SQLiteTranscriptRepository(TranscriptRepository):
    """SQLite 转写仓储实现"""

    def save(self, transcript: Transcript) -> None:
        """保存转写"""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO media_assets (
                        asset_id, transcript_path, transcript_status,
                        transcript_text, transcript_preview
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        transcript.asset_id,
                        str(transcript.path) if transcript.path else None,
                        transcript.status.value if hasattr(transcript, 'status') and transcript.status else "completed",
                        transcript.text,
                        transcript.preview,
                    ),
                )
            logger.debug(f"保存转写成功: asset_id={transcript.asset_id}")
        except Exception as e:
            logger.error(f"保存转写失败: asset_id={transcript.asset_id}, error={e}")
            raise

    def find_by_id(self, transcript_id: str) -> Optional[Transcript]:
        """按 ID 查询转写"""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    """
                    SELECT asset_id, transcript_path, transcript_text, transcript_preview
                    FROM media_assets
                    WHERE asset_id = ? AND transcript_status = 'completed'
                    LIMIT 1
                    """,
                    (transcript_id,),
                ).fetchone()
                if row:
                    return Transcript(
                        transcript_id=row[0],
                        asset_id=row[0],
                        text=row[2] if row[2] else "",
                        path=row[1],
                        preview=row[3],
                    )
                return None
        except Exception as e:
            logger.error(f"按ID查询转写失败: transcript_id={transcript_id}, error={e}")
            return None

    def find_by_asset(self, asset_id: str) -> Optional[Transcript]:
        """按素材 ID 查询转写"""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    """
                    SELECT asset_id, transcript_path, transcript_text, transcript_preview
                    FROM media_assets
                    WHERE asset_id = ? AND transcript_status = 'completed'
                    LIMIT 1
                    """,
                    (asset_id,),
                ).fetchone()
                if row:
                    return Transcript(
                        transcript_id=asset_id,
                        asset_id=asset_id,
                        text=row[2] if row[2] else "",
                        path=row[1],
                        preview=row[3],
                    )
                return None
        except Exception as e:
            logger.error(f"按素材ID查询转写失败: asset_id={asset_id}, error={e}")
            return None

    def find_all(self) -> List[Transcript]:
        """查询所有转写"""
        try:
            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT asset_id, transcript_path, transcript_text, transcript_preview
                    FROM media_assets
                    WHERE transcript_status = 'completed'
                    """
                ).fetchall()
                return [
                    Transcript(
                        transcript_id=row[0],
                        asset_id=row[0],
                        text=row[2] if row[2] else "",
                        path=row[1],
                        preview=row[3],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"查询所有转写失败: error={e}")
            return []

    def delete(self, transcript_id: str) -> None:
        """删除转写"""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE media_assets
                    SET transcript_path = NULL, transcript_status = 'none',
                        transcript_text = NULL, transcript_preview = NULL
                    WHERE asset_id = ?
                    """,
                    (transcript_id,),
                )
            logger.debug(f"删除转写成功: transcript_id={transcript_id}")
        except Exception as e:
            logger.error(f"删除转写失败: transcript_id={transcript_id}, error={e}")
            raise

    def exists(self, asset_id: str) -> bool:
        """检查素材是否已有转写"""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM media_assets WHERE asset_id = ? AND transcript_status = 'completed'",
                    (asset_id,),
                ).fetchone()
                return row is not None
        except Exception as e:
            logger.error(f"检查转写是否存在失败: asset_id={asset_id}, error={e}")
            return False

    def update_preview(self, transcript_id: str, preview: str) -> None:
        """更新转写预览"""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE media_assets SET transcript_preview = ? WHERE asset_id = ?",
                    (preview, transcript_id),
                )
            logger.debug(f"更新转写预览成功: transcript_id={transcript_id}")
        except Exception as e:
            logger.error(f"更新转写预览失败: transcript_id={transcript_id}, error={e}")
            raise


def create_transcript_repository() -> TranscriptRepository:
    """创建 TranscriptRepository 实例"""
    return SQLiteTranscriptRepository()
