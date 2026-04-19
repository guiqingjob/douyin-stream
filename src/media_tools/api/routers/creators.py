from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from media_tools.douyin.core.config_mgr import get_config
from media_tools.db.core import get_db_connection
import asyncio
import os
import sqlite3
import shutil
import logging
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api/v1/creators", tags=["creators"])
logger = logging.getLogger(__name__)

# Bilibili API 并发限制
_bilibili_semaphore = asyncio.Semaphore(5)  # 最多 5 个并发请求


async def _fetch_bilibili_nickname(mid: str, retries: int = 3) -> str:
    """
    异步获取 B 站用户昵称

    - 超时控制: connect=5s, read=10s
    - 重试: 最多 3 次，指数退避
    - 异常: 返回 mid 作为后备
    """
    import httpx

    url = f"https://api.bilibili.com/x/web-interface/card?mid={mid}"
    timeout = httpx.Timeout(connect=5.0, read=10.0)

    for attempt in range(retries):
        try:
            async with _bilibili_semaphore:  # 限制并发
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        if data.get("card"):
                            return data["card"].get("name") or mid
                    elif resp.status_code == 404:
                        logger.warning(f"B站用户不存在: mid={mid}")
                        return mid
                    else:
                        logger.warning(f"B站API返回非200: {resp.status_code}, mid={mid}")
        except httpx.TimeoutException:
            wait = 2 ** attempt
            logger.warning(f"B站API超时 (attempt {attempt + 1}/{retries}), 重试等待 {wait}s: mid={mid}")
            if attempt < retries - 1:
                await asyncio.sleep(wait)
        except httpx.HTTPError as e:
            wait = 2 ** attempt
            logger.warning(f"B站API错误 (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(wait)
        except Exception as e:
            logger.error(f"B站API异常: {e}")
            break

    return mid  # 所有重试失败，使用 mid 作为后备


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

def _resolve_query_value(val, default):
    """Convert Query object to actual value."""
    if hasattr(val, 'default'):
        return val.default if val.default is not None else default
    return val if val is not None else default


@router.get("/")
def list_creators(
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    offset: Optional[int] = Query(default=None, ge=0),
):
    limit = _resolve_query_value(limit, 100)
    offset = _resolve_query_value(offset, 0)
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
                    c.homepage_url,
                    c.last_fetch_time,
                    COUNT(ma.asset_id) AS asset_count,
                    COALESCE(SUM(CASE WHEN ma.video_status = 'downloaded' THEN 1 ELSE 0 END), 0) AS downloaded_videos_count,
                    COALESCE(SUM(CASE WHEN ma.transcript_status = 'completed' THEN 1 ELSE 0 END), 0) AS transcript_completed_count,
                    COALESCE(SUM(CASE WHEN ma.transcript_status = 'completed' AND (ma.is_read = 0 OR ma.is_read IS NULL) THEN 1 ELSE 0 END), 0) AS unread_completed_count,
                    COALESCE(SUM(CASE WHEN ma.transcript_status NOT IN ('completed', 'none') THEN 1 ELSE 0 END), 0) AS transcript_pending_count
                FROM creators c
                LEFT JOIN media_assets ma ON ma.creator_uid = c.uid
                GROUP BY c.uid, c.nickname, c.sec_user_id, c.sync_status, c.avatar, c.bio, c.homepage_url, c.last_fetch_time
                ORDER BY
                    CASE WHEN c.last_fetch_time IS NULL THEN 1 ELSE 0 END,
                    c.last_fetch_time DESC,
                    c.nickname COLLATE NOCASE ASC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        logger.exception("list_creators failed")
        return []


@router.post("/")
async def create_creator(req: CreatorCreateRequest):
    try:
        if "bilibili.com" in req.url or "b23.tv" in req.url:
            from media_tools.bilibili.core.url_parser import BilibiliUrlKind, normalize_bilibili_url
            from media_tools.bilibili.utils.naming import build_bilibili_creator_uid

            parsed = normalize_bilibili_url(req.url)
            if parsed.kind is not BilibiliUrlKind.SPACE or not parsed.mid:
                raise HTTPException(status_code=400, detail="暂只支持 B 站 UP 主空间链接（space.bilibili.com/<mid>）")

            uid = build_bilibili_creator_uid(parsed.mid)

            # 尝试获取B站用户真实昵称（异步，不阻塞线程池）
            nickname = parsed.mid
            homepage_url = f"https://space.bilibili.com/{parsed.mid}"
            try:
                nickname = await _fetch_bilibili_nickname(parsed.mid)
            except Exception as e:
                logger.warning(f"获取B站昵称失败: {e}")
                # 使用 mid 作为后备

            with get_db_connection() as conn:
                # 先检查是否存在
                cursor = conn.execute("SELECT uid FROM creators WHERE uid = ?", (uid,))
                exists = cursor.fetchone() is not None

                if exists:
                    # 已存在则更新
                    conn.execute(
                        "UPDATE creators SET sec_user_id = ?, nickname = ?, homepage_url = ? WHERE uid = ?",
                        (parsed.mid, nickname, homepage_url, uid),
                    )
                else:
                    # 不存在则插入
                    conn.execute(
                        "INSERT INTO creators (uid, sec_user_id, nickname, homepage_url, platform, sync_status) VALUES (?, ?, ?, ?, 'bilibili', 'active')",
                        (uid, parsed.mid, nickname, homepage_url),
                    )
                conn.commit()

                created = not exists

            return {
                "status": "created" if created else "exists",
                "creator": {
                    "uid": uid,
                    "nickname": nickname,
                    "sec_user_id": parsed.mid,
                    "homepage_url": homepage_url,
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
            conn.execute("BEGIN IMMEDIATE")

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

            # Phase 1: 删除文件（先删文件）
            for asset in assets:
                video_path = asset['video_path']
                transcript_name = asset['transcript_path']

                # Delete video file
                if video_path:
                    full_video_path = _resolve_safe_path(config.get_download_path(), video_path)
                    if full_video_path and full_video_path.exists():
                        try:
                            full_video_path.unlink()
                        except OSError as e:
                            conn.rollback()
                            raise HTTPException(status_code=500, detail=f"删除视频失败: {full_video_path}")

                # Delete transcript file
                if transcript_name:
                    full_transcript_path = _resolve_safe_path(config.project_root / "transcripts", transcript_name)
                    if full_transcript_path and full_transcript_path.exists():
                        try:
                            full_transcript_path.unlink()
                        except OSError as e:
                            conn.rollback()
                            raise HTTPException(status_code=500, detail=f"删除转写失败: {full_transcript_path}")

            # Also try to delete the creator's download folder if it exists
            download_base = config.get_download_path().resolve()
            for folder_name in [nickname, uid]:
                if folder_name:
                    creator_dir = _resolve_safe_path(download_base, folder_name)
                    if creator_dir and creator_dir.exists() and creator_dir.is_dir():
                        try:
                            shutil.rmtree(creator_dir)
                        except OSError as e:
                            conn.rollback()
                            raise HTTPException(status_code=500, detail=f"删除创作者目录失败: {creator_dir}")

            # Phase 2: 删除 DB 记录（后删DB）
            conn.execute("DELETE FROM media_assets WHERE creator_uid = ?", (uid,))

            # Delete creator from database
            conn.execute("DELETE FROM creators WHERE uid = ?", (uid,))

            conn.commit()

            return {"status": "success", "message": f"Creator {uid} and all their assets deleted successfully"}

    except HTTPException:
        raise
    except OSError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
