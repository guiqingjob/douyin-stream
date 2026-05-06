"""SQLite AssetRepository 实现"""
from typing import List, Optional

from media_tools.db.core import get_db_connection
from media_tools.domain.entities.asset import Asset, TranscriptStatus, VideoStatus
from media_tools.domain.repositories.asset_repository import AssetRepository


class SQLiteAssetRepository(AssetRepository):
    """SQLite 素材仓储实现"""

    def save(self, asset: Asset) -> None:
        """保存素材"""
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO media_assets (
                    asset_id, creator_uid, title, video_path, video_status,
                    transcript_path, transcript_status, transcript_preview,
                    transcript_text, source_url, source_platform, duration,
                    folder_path, is_read, is_starred, transcript_last_error,
                    transcript_error_type, transcript_retry_count, transcript_failed_at,
                    last_task_id, create_time, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.asset_id,
                    asset.creator_uid,
                    asset.title,
                    str(asset.video_path) if asset.video_path else None,
                    asset.video_status.value,
                    str(asset.transcript_path) if asset.transcript_path else None,
                    asset.transcript_status.value,
                    asset.transcript_preview,
                    asset.transcript_text,
                    asset.source_url,
                    asset.source_platform,
                    asset.duration,
                    asset.folder_path,
                    asset.is_read,
                    asset.is_starred,
                    asset.transcript_last_error,
                    asset.transcript_error_type,
                    asset.transcript_retry_count,
                    asset.transcript_failed_at.isoformat() if asset.transcript_failed_at else None,
                    asset.last_task_id,
                    asset.create_time.isoformat(),
                    asset.update_time.isoformat(),
                ),
            )

    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        """按 ID 查询素材"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            row = conn.execute(
                """
                SELECT * FROM media_assets WHERE asset_id = ? LIMIT 1
                """,
                (asset_id,),
            ).fetchone()
            return Asset.from_dict(row) if row else None

    def find_by_creator(self, creator_uid: str) -> List[Asset]:
        """按创作者查询素材"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                """
                SELECT * FROM media_assets WHERE creator_uid = ? ORDER BY create_time DESC
                """,
                (creator_uid,),
            ).fetchall()
            return [Asset.from_dict(row) for row in rows]

    def find_all(self) -> List[Asset]:
        """查询所有素材"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute("SELECT * FROM media_assets ORDER BY create_time DESC").fetchall()
            return [Asset.from_dict(row) for row in rows]

    def find_by_status(
        self,
        video_status: Optional[str] = None,
        transcript_status: Optional[str] = None,
    ) -> List[Asset]:
        """按状态查询素材"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            query = "SELECT * FROM media_assets WHERE 1=1"
            params = []

            if video_status:
                query += " AND video_status = ?"
                params.append(video_status)

            if transcript_status:
                query += " AND transcript_status = ?"
                params.append(transcript_status)

            query += " ORDER BY create_time DESC"
            rows = conn.execute(query, params).fetchall()
            return [Asset.from_dict(row) for row in rows]

    def find_starred(self) -> List[Asset]:
        """查询收藏的素材"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM media_assets WHERE is_starred = 1 ORDER BY create_time DESC"
            ).fetchall()
            return [Asset.from_dict(row) for row in rows]

    def find_unread(self) -> List[Asset]:
        """查询未读素材"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM media_assets WHERE is_read = 0 ORDER BY create_time DESC"
            ).fetchall()
            return [Asset.from_dict(row) for row in rows]

    def delete(self, asset_id: str) -> None:
        """删除素材"""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))

    def exists(self, asset_id: str) -> bool:
        """检查素材是否存在"""
        with get_db_connection() as conn:
            row = conn.execute("SELECT 1 FROM media_assets WHERE asset_id = ?", (asset_id,)).fetchone()
            return row is not None

    def count_by_creator(self, creator_uid: str) -> int:
        """统计创作者的素材数量"""
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM media_assets WHERE creator_uid = ?",
                (creator_uid,),
            ).fetchone()
            return row[0] if row else 0

    def count_by_status(self, creator_uid: Optional[str] = None) -> dict:
        """按状态统计素材数量"""
        with get_db_connection() as conn:
            query = """
                SELECT video_status, transcript_status, COUNT(*) as count
                FROM media_assets
            """
            params = []

            if creator_uid:
                query += " WHERE creator_uid = ?"
                params.append(creator_uid)

            query += " GROUP BY video_status, transcript_status"
            rows = conn.execute(query, params).fetchall()

            result = {}
            for row in rows:
                video_status, transcript_status, count = row
                key = f"{video_status}_{transcript_status}"
                result[key] = count
                result[video_status] = result.get(video_status, 0) + count
                result[transcript_status] = result.get(transcript_status, 0) + count

            return result


def create_asset_repository() -> AssetRepository:
    """创建 AssetRepository 实例"""
    return SQLiteAssetRepository()