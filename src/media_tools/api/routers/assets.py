from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from media_tools.douyin.core.config_mgr import get_config
from media_tools.db.core import get_db_connection
from typing import Optional
import sqlite3
import logging
import io
import os
import zipfile
from pathlib import Path

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])
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

@router.get("/")
def list_assets(creator_uid: Optional[str] = Query(None)):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            base_sql = "SELECT asset_id, creator_uid, title, video_status, transcript_status, transcript_path, folder_path, is_read, is_starred, create_time, update_time FROM media_assets"
            if creator_uid:
                cursor = conn.execute(base_sql + " WHERE creator_uid = ?", (creator_uid,))
            else:
                cursor = conn.execute(base_sql)
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        logger.exception("list_assets failed")
        return []

@router.get("/search")
def search_assets(q: str = Query(..., min_length=1)):
    """搜索素材标题和转写文稿内容"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            # 搜索标题
            cursor = conn.execute(
                """SELECT asset_id, creator_uid, title, video_status, transcript_status, transcript_path
                   FROM media_assets
                   WHERE title LIKE ? OR asset_id IN (
                       SELECT asset_id FROM media_assets WHERE transcript_path IS NOT NULL
                   )
                   LIMIT 50""",
                (f"%{q}%",)
            )
            results = [dict(row) for row in cursor.fetchall()]

            # 对有转写文件的结果，检查文稿内容是否匹配
            config = get_config()
            transcripts_dir = config.project_root / "transcripts"
            matched = []
            for asset in results:
                # 标题匹配直接加入
                if q.lower() in (asset.get('title') or '').lower():
                    asset['match_type'] = 'title'
                    matched.append(asset)
                    continue
                # 检查文稿内容
                if asset.get('transcript_path'):
                    transcript_file = _resolve_safe_path(transcripts_dir, asset['transcript_path'])
                    if transcript_file and transcript_file.exists():
                        try:
                            content = transcript_file.read_text(encoding='utf-8')
                            if q.lower() in content.lower():
                                asset['match_type'] = 'content'
                                matched.append(asset)
                        except Exception:
                            pass
            return matched
    except Exception as e:
        logger.exception("search_assets failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
def export_transcripts(asset_ids: list[str]):
    """批量导出转写文稿为 zip"""
    config = get_config()
    transcripts_dir = config.project_root / "transcripts"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ','.join('?' * len(asset_ids))
            cursor = conn.execute(
                f"SELECT asset_id, title, transcript_path FROM media_assets WHERE asset_id IN ({placeholders}) AND transcript_path IS NOT NULL",
                asset_ids
            )
            for row in cursor.fetchall():
                transcript_file = _resolve_safe_path(transcripts_dir, row['transcript_path'])
                if transcript_file and transcript_file.exists():
                    filename = f"{row['title'] or row['asset_id']}.md"
                    # 清理文件名
                    filename = ''.join(c for c in filename if c not in '<>:"/\\|?*')
                    zf.writestr(filename, transcript_file.read_text(encoding='utf-8'))

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=transcripts.zip"}
    )


@router.get("/{asset_id}/transcript")
def get_transcript(asset_id: str):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT transcript_path FROM media_assets WHERE asset_id = ?", (asset_id,))
            row = cursor.fetchone()

        if not row or not row["transcript_path"]:
            raise HTTPException(status_code=404, detail="Transcript not found in database")

        transcript_name = row["transcript_path"]
        config = get_config()
        transcripts_dir = config.project_root / "transcripts"
        transcript_file = _resolve_safe_path(transcripts_dir, transcript_name)

        if not transcript_file or not transcript_file.exists():
            with get_db_connection() as conn:
                conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
                conn.commit()
            raise HTTPException(status_code=404, detail="Transcript file not found on disk")

        content = transcript_file.read_text(encoding="utf-8")
        return {"content": content}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{asset_id}")
def delete_asset(asset_id: str):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT video_path, transcript_path FROM media_assets WHERE asset_id = ?", (asset_id,))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Asset not found")
                
            video_path = row['video_path']
            transcript_name = row['transcript_path']

            config = get_config()

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
            
            # Delete from database
            conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
            conn.commit()
            
            return {"status": "success", "message": f"Asset {asset_id} deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AssetMarkRequest(BaseModel):
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None

@router.patch("/{asset_id}/mark")
def mark_asset(asset_id: str, req: AssetMarkRequest):
    """标记素材为已读/收藏"""
    updates = []
    params = []
    if req.is_read is not None:
        updates.append("is_read = ?")
        params.append(req.is_read)
    if req.is_starred is not None:
        updates.append("is_starred = ?")
        params.append(req.is_starred)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("update_time = CURRENT_TIMESTAMP")
    params.append(asset_id)

    with get_db_connection() as conn:
        conn.execute(f"UPDATE media_assets SET {', '.join(updates)} WHERE asset_id = ?", params)
        conn.commit()
    return {"status": "success"}


class BulkAssetMarkRequest(BaseModel):
    ids: list[str]
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None


@router.post("/bulk_mark")
def bulk_mark_assets(req: BulkAssetMarkRequest):
    """批量标记素材为已读/收藏"""
    if not req.ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    if req.is_read is None and req.is_starred is None:
        raise HTTPException(status_code=400, detail="至少指定 is_read 或 is_starred")

    set_clauses = []
    set_params: list = []
    if req.is_read is not None:
        set_clauses.append("is_read = ?")
        set_params.append(req.is_read)
    if req.is_starred is not None:
        set_clauses.append("is_starred = ?")
        set_params.append(req.is_starred)
    set_clauses.append("update_time = CURRENT_TIMESTAMP")

    updated = 0
    with get_db_connection() as conn:
        for start in range(0, len(req.ids), 500):
            chunk = req.ids[start:start + 500]
            placeholders = ",".join("?" * len(chunk))
            sql = f"UPDATE media_assets SET {', '.join(set_clauses)} WHERE asset_id IN ({placeholders})"
            cursor = conn.execute(sql, (*set_params, *chunk))
            updated += cursor.rowcount
        conn.commit()
    return {"status": "success", "updated": updated}
