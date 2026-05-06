"""AssetService - 素材管理服务层"""
from __future__ import annotations

import io
import logging
import sqlite3
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from media_tools.common.paths import get_download_path, get_project_root
from media_tools.db.core import get_db_connection, resolve_safe_path, resolve_query_value
from media_tools.services.asset_file_ops import (
    delete_asset_files,
    get_source_url_column,
    _resolve_asset_video_file,
)
from media_tools.services.asset_gc import cleanup_stale_assets

logger = logging.getLogger(__name__)
LOCAL_CREATOR_UID = "local:upload"


class AssetService:
    """素材管理服务 - 封装素材相关业务逻辑"""
    
    @staticmethod
    def list_assets(
        creator_uid: Optional[str] = None,
        transcript_status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        silent: bool = False,
    ) -> List[Dict[str, Any]]:
        """获取素材列表"""
        limit = resolve_query_value(limit, 100)
        offset = resolve_query_value(offset, 0)

        allowed_statuses = {"completed", "pending", "none", "failed"}
        status_filter: List[str] = []
        if transcript_status:
            for token in transcript_status.split(","):
                t = token.strip().lower()
                if t and t in allowed_statuses:
                    status_filter.append(t)
            status_filter = list(dict.fromkeys(status_filter))

        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                base_sql = (
                    "SELECT asset_id, creator_uid, title, video_status, transcript_status, "
                    "transcript_path, transcript_preview, folder_path, is_read, is_starred, "
                    "transcript_error_type, transcript_last_error, transcript_retry_count, "
                    "transcript_failed_at, source_platform, last_task_id, "
                    "create_time, update_time FROM media_assets"
                )

                where_clauses: List[str] = []
                params: List = []
                if creator_uid:
                    where_clauses.append("creator_uid = ?")
                    params.append(creator_uid)
                if status_filter:
                    placeholders = ",".join(["?"] * len(status_filter))
                    where_clauses.append(f"transcript_status IN ({placeholders})")
                    params.extend(status_filter)

                sql = base_sql
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
                sql += " ORDER BY update_time DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.exception(f"list_assets failed: {e}")
            if silent:
                return []
            raise
    
    @staticmethod
    def get_asset(asset_id: str) -> Optional[Dict[str, Any]]:
        """获取单个素材"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT asset_id, creator_uid, title, video_status, transcript_status, "
                    "transcript_path, transcript_preview, folder_path, is_read, is_starred, "
                    "transcript_error_type, transcript_last_error, transcript_retry_count, "
                    "transcript_failed_at, source_platform, source_url, last_task_id, "
                    "create_time, update_time FROM media_assets WHERE asset_id = ?",
                    (asset_id,)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.exception(f"get_asset failed for {asset_id}: {e}")
            raise
    
    @staticmethod
    def delete_asset(asset_id: str) -> Dict[str, str]:
        """删除素材"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT creator_uid, folder_path FROM media_assets WHERE asset_id = ?",
                    (asset_id,)
                ).fetchone()
                if not row:
                    return {"error": "素材不存在"}

                # 删除文件
                folder_path = row["folder_path"]
                if folder_path:
                    delete_asset_files(folder_path)

                # 删除数据库记录
                conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
                conn.commit()

            return {"status": "ok"}
        except sqlite3.Error as e:
            logger.exception(f"delete_asset failed for {asset_id}: {e}")
            raise
        except OSError as e:
            logger.exception(f"delete_asset_files failed for {asset_id}: {e}")
            raise
    
    @staticmethod
    def mark_asset_read(asset_id: str, is_read: bool) -> Dict[str, str]:
        """标记素材已读/未读"""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE media_assets SET is_read = ? WHERE asset_id = ?",
                    (is_read, asset_id)
                )
                conn.commit()
            return {"status": "ok"}
        except sqlite3.Error as e:
            logger.exception(f"mark_asset_read failed for {asset_id}: {e}")
            raise
    
    @staticmethod
    def toggle_starred(asset_id: str) -> Dict[str, Any]:
        """切换素材收藏状态"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT is_starred FROM media_assets WHERE asset_id = ?",
                    (asset_id,)
                ).fetchone()
                if not row:
                    return {"error": "素材不存在"}

                new_state = not row["is_starred"]
                conn.execute(
                    "UPDATE media_assets SET is_starred = ? WHERE asset_id = ?",
                    (new_state, asset_id)
                )
                conn.commit()

            return {"status": "ok", "is_starred": new_state}
        except sqlite3.Error as e:
            logger.exception(f"toggle_starred failed for {asset_id}: {e}")
            raise
    
    @staticmethod
    def cleanup_stale_assets(dry_run: bool = False) -> Dict[str, Any]:
        """清理过期素材"""
        try:
            result = cleanup_stale_assets(dry_run=dry_run)
            return result
        except Exception as e:
            logger.exception(f"cleanup_stale_assets failed: {e}")
            raise
    
    @staticmethod
    def download_asset_video(asset_id: str) -> StreamingResponse:
        """下载素材视频"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT title, folder_path, creator_uid FROM media_assets WHERE asset_id = ?",
                    (asset_id,)
                ).fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="素材不存在")

                video_path = _resolve_asset_video_file(row["folder_path"], row["creator_uid"])
                if not video_path or not video_path.exists():
                    raise HTTPException(status_code=404, detail="视频文件不存在")

                def iterfile():
                    with open(video_path, "rb") as f:
                        yield from f

                filename = f"{row['title']}.mp4"
                return StreamingResponse(
                    iterfile(),
                    media_type="video/mp4",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )
        except sqlite3.Error as e:
            logger.exception(f"download_asset_video failed for {asset_id}: {e}")
            raise
    
    @staticmethod
    def download_transcript(asset_id: str) -> StreamingResponse:
        """下载转写文件"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT title, transcript_path FROM media_assets WHERE asset_id = ?",
                    (asset_id,)
                ).fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="素材不存在")

                transcript_path = Path(row["transcript_path"]) if row["transcript_path"] else None
                if not transcript_path or not transcript_path.exists():
                    raise HTTPException(status_code=404, detail="转写文件不存在")

                def iterfile():
                    with open(transcript_path, "rb") as f:
                        yield from f

                filename = f"{row['title']}.md"
                return StreamingResponse(
                    iterfile(),
                    media_type="text/markdown",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )
        except sqlite3.Error as e:
            logger.exception(f"download_transcript failed for {asset_id}: {e}")
            raise


# 全局实例
_asset_service: Optional[AssetService] = None


def get_asset_service() -> AssetService:
    """获取 AssetService 实例"""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service