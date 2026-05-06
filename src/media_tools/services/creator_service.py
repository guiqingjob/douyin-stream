from __future__ import annotations
"""CreatorService - 创作者管理服务层（迁移过渡版本）

本文件作为迁移过渡层，逐步将业务逻辑委托给新的领域驱动架构。
最终目标是完全移除本文件，直接使用新架构。
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from media_tools.common.paths import get_download_path
from media_tools.db.core import get_db_connection
from media_tools.douyin.core.following_mgr import list_users
from media_tools.douyin.core.video_scanner import scan_local_videos

# 新架构导入（迁移使用）
from media_tools.migration import get_migration_service, get_creator_service as get_new_creator_service

logger = logging.getLogger(__name__)


class CreatorService:
    """创作者管理服务 - 封装创作者相关业务逻辑"""
    
    @staticmethod
    def list_creators() -> List[Dict[str, Any]]:
        """获取创作者列表（使用新架构）"""
        try:
            new_service = get_new_creator_service()
            creators = new_service.list_creators()
            return [CreatorService._creator_entity_to_dict(creator) for creator in creators]
        except Exception as e:
            logger.exception(f"list_creators failed: {e}")
            # 降级到旧实现
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT uid, nickname, avatar_url, last_fetch_time, video_count, "
                    "downloaded_count, transcript_count, status FROM creators "
                    "ORDER BY nickname ASC"
                ).fetchall()
                return [dict(row) for row in rows]
    
    @staticmethod
    def get_creator(uid: str) -> Optional[Dict[str, Any]]:
        """获取单个创作者（使用新架构）"""
        try:
            new_service = get_new_creator_service()
            creator = new_service.get_creator(uid)
            if creator:
                return CreatorService._creator_entity_to_dict(creator)
            return None
        except Exception as e:
            logger.exception(f"get_creator failed for {uid}: {e}")
            # 降级到旧实现
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT uid, nickname, avatar_url, last_fetch_time, video_count, "
                    "downloaded_count, transcript_count, status FROM creators WHERE uid = ?",
                    (uid,)
                ).fetchone()
                return dict(row) if row else None
    
    @staticmethod
    def add_creator(uid: str, nickname: str, avatar_url: str = "") -> Dict[str, str]:
        """添加创作者（使用新架构）"""
        try:
            new_service = get_new_creator_service()
            new_service.create_creator(uid, nickname, avatar_url)
            return {"status": "ok"}
        except Exception as e:
            logger.exception(f"add_creator failed for {uid}: {e}")
            # 降级到旧实现
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO creators (uid, nickname, avatar_url, status) "
                    "VALUES (?, ?, ?, 'active')",
                    (uid, nickname, avatar_url)
                )
                conn.commit()
            return {"status": "ok"}
    
    @staticmethod
    def update_creator(uid: str, nickname: Optional[str] = None, avatar_url: Optional[str] = None) -> Dict[str, str]:
        """更新创作者信息（使用新架构）"""
        try:
            updates = {}
            if nickname:
                updates["nickname"] = nickname
            if avatar_url:
                updates["avatar_url"] = avatar_url
            
            new_service = get_new_creator_service()
            new_service.update_creator(uid, **updates)
            return {"status": "ok"}
        except Exception as e:
            logger.exception(f"update_creator failed for {uid}: {e}")
            # 降级到旧实现
            with get_db_connection() as conn:
                updates_list = []
                params = []
                
                if nickname:
                    updates_list.append("nickname = ?")
                    params.append(nickname)
                if avatar_url:
                    updates_list.append("avatar_url = ?")
                    params.append(avatar_url)
                
                if not updates_list:
                    return {"status": "ok"}
                
                params.append(uid)
                conn.execute(
                    f"UPDATE creators SET {', '.join(updates_list)} WHERE uid = ?",
                    params
                )
                conn.commit()
            return {"status": "ok"}
    
    @staticmethod
    def delete_creator(uid: str) -> Dict[str, str]:
        """删除创作者（使用新架构）"""
        try:
            new_service = get_new_creator_service()
            new_service.delete_creator(uid)
            return {"status": "ok"}
        except Exception as e:
            logger.exception(f"delete_creator failed for {uid}: {e}")
            # 降级到旧实现
            with get_db_connection() as conn:
                conn.execute("DELETE FROM media_assets WHERE creator_uid = ?", (uid,))
                conn.execute("DELETE FROM creators WHERE uid = ?", (uid,))
                conn.commit()
            return {"status": "ok"}
    
    @staticmethod
    def refresh_creator_videos(uid: str) -> Dict[str, Any]:
        """刷新创作者视频列表"""
        try:
            result = scan_local_videos()
            return result
        except Exception as e:
            logger.exception(f"refresh_creator_videos failed for {uid}: {e}")
            raise
    
    @staticmethod
    def get_following_list() -> List[Dict[str, Any]]:
        """获取关注列表（从抖音 API）"""
        try:
            users = list_users()
            return users
        except Exception as e:
            logger.exception("get_following_list failed: {e}")
            raise
    
    @staticmethod
    def get_creator_folder_path(uid: str, nickname: str) -> Path:
        """获取创作者文件夹路径"""
        download_path = get_download_path()
        safe_name = CreatorService._clean_name(nickname) or uid
        return download_path / safe_name
    
    @staticmethod
    def _clean_name(name: str) -> str:
        """清理文件名中的非法字符"""
        import re
        return re.sub(r'[\\/*?:"<>|]', '_', name)
    
    @staticmethod
    def _creator_entity_to_dict(creator) -> Dict[str, Any]:
        """将新架构的 Creator 实体转换为字典格式（兼容旧 API）"""
        return {
            "uid": creator.uid,
            "nickname": creator.nickname,
            "avatar_url": creator.avatar_url,
            "video_count": creator.video_count,
            "downloaded_count": creator.downloaded_count,
            "transcript_count": creator.transcript_count,
            "last_fetch_time": creator.last_fetch_time.isoformat() if creator.last_fetch_time else None,
            "status": creator.status,
        }


# 全局实例（保持向后兼容）
_creator_service: Optional[CreatorService] = None


def get_creator_service() -> CreatorService:
    """获取 CreatorService 实例（保持向后兼容）"""
    global _creator_service
    if _creator_service is None:
        _creator_service = CreatorService()
    return _creator_service