from __future__ import annotations
"""AssetService - 素材管理服务层（迁移过渡版本）

本文件作为迁移过渡层，逐步将业务逻辑委托给新的领域驱动架构。
最终目标是完全移除本文件，直接使用新架构。
"""

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

# 新架构导入（迁移使用）
from media_tools.migration import get_migration_service, get_asset_service as get_new_asset_service

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
        """获取素材列表（使用新架构）"""
        limit = resolve_query_value(limit, 100)
        offset = resolve_query_value(offset, 0)
        
        try:
            new_service = get_new_asset_service()
            assets = new_service.list_assets(creator_uid)
            # 分页处理
            assets = assets[offset : offset + limit]
            return [AssetService._asset_entity_to_dict(asset) for asset in assets]
        except Exception as e:
            logger.exception(f"list_assets failed: {e}")
            if silent:
                return []
            # 降级到旧实现
            return AssetService._list_assets_legacy(creator_uid, transcript_status, limit, offset)
    
    @staticmethod
    def _list_assets_legacy(
        creator_uid: Optional[str] = None,
        transcript_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取素材列表（旧实现，用于降级）"""
        allowed_statuses = {"completed", "pending", "none", "failed"}
        status_filter: List[str] = []
        if transcript_status:
            for token in transcript_status.split(","):
                t = token.strip().lower()
                if t and t in allowed_statuses:
                    status_filter.append(t)
            status_filter = list(dict.fromkeys(status_filter))
        
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
    
    @staticmethod
    def get_asset(asset_id: str) -> Optional[Dict[str, Any]]:
        """获取单个素材（使用新架构）"""
        try:
            new_service = get_new_asset_service()
            asset = new_service.get_asset(asset_id)
            if asset:
                return AssetService._asset_entity_to_dict(asset)
            return None
        except Exception as e:
            logger.exception(f"get_asset failed for {asset_id}: {e}")
            # 降级到旧实现
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
    
    @staticmethod
    def delete_asset(asset_id: str) -> Dict[str, str]:
        """删除素材（使用新架构）"""
        try:
            # 获取素材信息用于文件删除
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT folder_path FROM media_assets WHERE asset_id = ?",
                    (asset_id,)
                ).fetchone()
                
                if row:
                    folder_path = row["folder_path"]
                    if folder_path:
                        delete_asset_files(folder_path)
            
            # 使用新架构删除素材
            new_service = get_new_asset_service()
            new_service.delete_asset(asset_id)
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
                
                new_value = not row["is_starred"]
                conn.execute(
                    "UPDATE media_assets SET is_starred = ? WHERE asset_id = ?",
                    (new_value, asset_id)
                )
                conn.commit()
                return {"status": "ok", "is_starred": new_value}
        except sqlite3.Error as e:
            logger.exception(f"toggle_starred failed for {asset_id}: {e}")
            raise
    
    @staticmethod
    def cleanup_stale_assets() -> Dict[str, Any]:
        """清理过期素材"""
        try:
            result = cleanup_stale_assets()
            return result
        except Exception as e:
            logger.exception(f"cleanup_stale_assets failed: {e}")
            raise
    
    @staticmethod
    def _asset_entity_to_dict(asset) -> Dict[str, Any]:
        """将新架构的 Asset 实体转换为字典格式（兼容旧 API）"""
        return {
            "asset_id": asset.asset_id,
            "creator_uid": asset.creator_uid,
            "title": asset.title,
            "video_path": str(asset.video_path) if asset.video_path else None,
            "video_status": asset.video_status.value,
            "transcript_path": str(asset.transcript_path) if asset.transcript_path else None,
            "transcript_status": asset.transcript_status.value,
            "transcript_preview": asset.transcript_preview,
            "source_platform": asset.source_platform,
            "source_url": asset.source_url,
            "is_read": asset.is_read,
            "is_starred": asset.is_starred,
            "create_time": asset.create_time.isoformat(),
            "update_time": asset.update_time.isoformat(),
        }


# 全局实例（保持向后兼容）
_asset_service: Optional[AssetService] = None


def get_asset_service() -> AssetService:
    """获取 AssetService 实例（保持向后兼容）"""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service