from fastapi import APIRouter, HTTPException
from media_tools.douyin.core.config_mgr import get_config
from media_tools.db.core import get_db_connection
import os
import sqlite3
import shutil
import logging
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api/v1/creators", tags=["creators"])
logger = logging.getLogger(__name__)


def _resolve_safe_path(base_dir: Path, relative_path: str | None) -> Path | None:
    """Resolve a path and ensure it stays within base_dir."""
    if not relative_path:
        return None
    try:
        base = base_dir.resolve()
        target = (base / relative_path).resolve()
        if not str(target).startswith(str(base) + os.sep) and str(target) != str(base):
            logger.warning(f"Path traversal blocked: {relative_path} -> {target}")
            return None
        return target
    except Exception:
        return None


class CreatorCreateRequest(BaseModel):
    url: str

@router.get("/")
def list_creators():
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    c.uid,
                    c.nickname,
                    c.sec_user_id,
                    c.sync_status,
                    c.avatar,
                    c.bio,
                    c.last_fetch_time,
                    COUNT(ma.asset_id) AS asset_count,
                    COALESCE(SUM(CASE WHEN ma.video_status = 'downloaded' THEN 1 ELSE 0 END), 0) AS downloaded_videos_count,
                    COALESCE(SUM(CASE WHEN ma.transcript_status = 'completed' THEN 1 ELSE 0 END), 0) AS transcript_completed_count,
                    COALESCE(SUM(CASE WHEN ma.transcript_status NOT IN ('completed', 'none') THEN 1 ELSE 0 END), 0) AS transcript_pending_count
                FROM creators c
                LEFT JOIN media_assets ma ON ma.creator_uid = c.uid
                GROUP BY c.uid, c.nickname, c.sec_user_id, c.sync_status, c.avatar, c.bio, c.last_fetch_time
                ORDER BY
                    CASE WHEN c.last_fetch_time IS NULL THEN 1 ELSE 0 END,
                    c.last_fetch_time DESC,
                    c.nickname COLLATE NOCASE ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        logger.exception("list_creators failed")
        return []


@router.post("/")
def create_creator(req: CreatorCreateRequest):
    try:
        if "bilibili.com" in req.url or "b23.tv" in req.url:
            from media_tools.bilibili.core.url_parser import BilibiliUrlKind, normalize_bilibili_url
            from media_tools.bilibili.utils.naming import build_bilibili_creator_uid

            parsed = normalize_bilibili_url(req.url)
            if parsed.kind is not BilibiliUrlKind.SPACE or not parsed.mid:
                raise HTTPException(status_code=400, detail="暂只支持 B 站 UP 主空间链接（space.bilibili.com/<mid>）")

            uid = build_bilibili_creator_uid(parsed.mid)
            nickname = uid

            with get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO creators (uid, sec_user_id, nickname, platform, sync_status)
                    VALUES (?, ?, ?, 'bilibili', 'active')
                    """,
                    (uid, parsed.mid, nickname),
                )
                conn.commit()

                created = cursor.rowcount > 0

            return {
                "status": "created" if created else "exists",
                "creator": {
                    "uid": uid,
                    "nickname": nickname,
                    "sec_user_id": parsed.mid,
                    "sync_status": "active",
                },
            }

        from media_tools.douyin.core.following_mgr import add_user

        success, user_info = add_user(req.url)
        if success:
            return {"status": "created", "creator": user_info}
        if user_info:
            return {"status": "exists", "creator": user_info}
        raise HTTPException(status_code=400, detail="无法添加创作者，请检查主页链接是否有效")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{uid}")
def delete_creator(uid: str):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            # Check if creator exists
            cursor = conn.execute("SELECT nickname FROM creators WHERE uid = ?", (uid,))
            creator = cursor.fetchone()
            if not creator:
                raise HTTPException(status_code=404, detail="Creator not found")
                
            nickname = creator['nickname']
            
            # Find all assets for this creator
            cursor = conn.execute("SELECT asset_id, video_path, transcript_path FROM media_assets WHERE creator_uid = ?", (uid,))
            assets = cursor.fetchall()
            
            config = get_config()
            
            for asset in assets:
                video_path = asset['video_path']
                transcript_name = asset['transcript_path']

                # Delete video file
                if video_path:
                    full_video_path = _resolve_safe_path(config.get_download_path(), video_path)
                    if full_video_path and full_video_path.exists():
                        try:
                            full_video_path.unlink()
                        except Exception as e:
                            logger.warning(f"Failed to delete video file {full_video_path}: {e}")

                # Delete transcript file
                if transcript_name:
                    full_transcript_path = _resolve_safe_path(config.project_root / "transcripts", transcript_name)
                    if full_transcript_path and full_transcript_path.exists():
                        try:
                            full_transcript_path.unlink()
                        except Exception as e:
                            logger.warning(f"Failed to delete transcript file {full_transcript_path}: {e}")

            # Also try to delete the creator's download folder if it exists
            # Usually it's named after the nickname or uid
            download_base = config.get_download_path().resolve()
            for folder_name in [nickname, uid]:
                if folder_name:
                    creator_dir = _resolve_safe_path(download_base, folder_name)
                    if creator_dir and creator_dir.exists() and creator_dir.is_dir():
                        try:
                            shutil.rmtree(creator_dir)
                        except Exception as e:
                            logger.warning(f"Failed to delete creator directory {creator_dir}: {e}")
            
            # Delete assets from database
            conn.execute("DELETE FROM media_assets WHERE creator_uid = ?", (uid,))
            
            # Delete creator from database
            conn.execute("DELETE FROM creators WHERE uid = ?", (uid,))
            
            conn.commit()
            
            return {"status": "success", "message": f"Creator {uid} and all their assets deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
