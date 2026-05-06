"""SQLite CreatorRepository 实现"""
from typing import List, Optional

from media_tools.db.core import get_db_connection
from media_tools.domain.entities.creator import Creator, PlatformType, SyncStatus
from media_tools.domain.repositories.creator_repository import CreatorRepository


class SQLiteCreatorRepository(CreatorRepository):
    """SQLite 创作者仓储实现"""

    def save(self, creator: Creator) -> None:
        """保存创作者"""
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO creators (
                    uid, sec_user_id, nickname, platform, sync_status,
                    homepage_url, avatar, bio, last_fetch_time,
                    downloaded_count, transcript_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    creator.uid,
                    creator.sec_user_id,
                    creator.nickname,
                    creator.platform.value,
                    creator.sync_status.value,
                    creator.homepage_url,
                    creator.avatar,
                    creator.bio,
                    creator.last_fetch_time.isoformat() if creator.last_fetch_time else None,
                    creator.downloaded_count,
                    creator.transcript_count,
                ),
            )

    def find_by_id(self, uid: str) -> Optional[Creator]:
        """按 ID 查询创作者"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            row = conn.execute(
                "SELECT * FROM creators WHERE uid = ? LIMIT 1",
                (uid,),
            ).fetchone()
            return Creator.from_dict(row) if row else None

    def find_all(self) -> List[Creator]:
        """查询所有创作者"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute("SELECT * FROM creators ORDER BY nickname").fetchall()
            return [Creator.from_dict(row) for row in rows]

    def find_by_platform(self, platform: str) -> List[Creator]:
        """按平台查询创作者"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM creators WHERE platform = ? ORDER BY nickname",
                (platform,),
            ).fetchall()
            return [Creator.from_dict(row) for row in rows]

    def find_active(self) -> List[Creator]:
        """查询活跃的创作者"""
        with get_db_connection() as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            rows = conn.execute(
                "SELECT * FROM creators WHERE sync_status = ? ORDER BY nickname",
                (SyncStatus.ACTIVE.value,),
            ).fetchall()
            return [Creator.from_dict(row) for row in rows]

    def delete(self, uid: str) -> None:
        """删除创作者"""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM creators WHERE uid = ?", (uid,))

    def exists(self, uid: str) -> bool:
        """检查创作者是否存在"""
        with get_db_connection() as conn:
            row = conn.execute("SELECT 1 FROM creators WHERE uid = ?", (uid,)).fetchone()
            return row is not None

    def update_downloaded_count(self, uid: str, count: int) -> None:
        """更新下载计数"""
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE creators SET downloaded_count = ? WHERE uid = ?",
                (count, uid),
            )

    def update_transcript_count(self, uid: str, count: int) -> None:
        """更新转写计数"""
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE creators SET transcript_count = ? WHERE uid = ?",
                (count, uid),
            )


def create_creator_repository() -> CreatorRepository:
    """创建 CreatorRepository 实例"""
    return SQLiteCreatorRepository()