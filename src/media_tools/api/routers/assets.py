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
LOCAL_CREATOR_UID = "local:upload"


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
    except (OSError, ValueError):
        # 路径解析失败（文件不存在、权限问题、无效路径等）
        return None


def _resolve_asset_video_file(
    *,
    creator_uid: str | None,
    source_url: str | None,
    video_path: str | None,
    download_dir: Path,
) -> Path | None:
    if creator_uid == LOCAL_CREATOR_UID and source_url:
        try:
            return Path(source_url).resolve()
        except (OSError, ValueError):
            return None
    return _resolve_safe_path(download_dir, video_path)


def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        row["name"] if isinstance(row, sqlite3.Row) else row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }

def _resolve_query_value(val, default):
    """Convert Query object to actual value."""
    if hasattr(val, 'default'):
        return val.default if val.default is not None else default
    return val if val is not None else default


@router.get("/")
def list_assets(
    creator_uid: Optional[str] = Query(None),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    offset: Optional[int] = Query(default=None, ge=0),
    silent: bool = Query(default=False, description="返回空列表而非抛错（兼容旧版）"),
):
    """
    获取素材列表

    - silent=false（默认）：数据库错误抛 500
    - silent=true：数据库错误返回空列表（兼容旧版）
    """
    import sqlite3

    limit = _resolve_query_value(limit, 100)
    offset = _resolve_query_value(offset, 0)

    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            base_sql = "SELECT asset_id, creator_uid, title, video_status, transcript_status, transcript_path, transcript_preview, folder_path, is_read, is_starred, create_time, update_time FROM media_assets"
            if creator_uid:
                cursor = conn.execute(
                    base_sql + " WHERE creator_uid = ? ORDER BY update_time DESC LIMIT ? OFFSET ?",
                    (creator_uid, limit, offset)
                )
            else:
                cursor = conn.execute(
                    base_sql + " ORDER BY update_time DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            return [dict(row) for row in cursor.fetchall()]

    except sqlite3.OperationalError as e:
        # 数据库错误（表不存在、语法错误等）
        logger.error(f"list_assets 数据库错误: creator_uid={creator_uid}, limit={limit}, offset={offset}, error={e}")
        logger.exception("list_assets 数据库错误详情")
        if silent:
            return []
        raise HTTPException(
            status_code=500,
            detail={"detail": "Database error", "type": "database_error", "message": str(e)}
        )

    except sqlite3.IntegrityError as e:
        # 数据完整性错误
        logger.error(f"list_assets 数据完整性错误: {e}")
        logger.exception("list_assets 完整性错误详情")
        if silent:
            return []
        raise HTTPException(
            status_code=500,
            detail={"detail": "Data integrity error", "type": "integrity_error", "message": str(e)}
        )

    except Exception as e:
        # 其他未预期异常
        logger.error(f"list_assets 未知错误: creator_uid={creator_uid}, limit={limit}, offset={offset}")
        logger.exception("list_assets 未知错误详情")
        if silent:
            return []
        raise HTTPException(
            status_code=500,
            detail={"detail": "Internal error", "type": "internal_error", "message": str(e)}
        )

@router.get("/search")
def search_assets(q: str = Query(..., min_length=1)):
    """搜索素材标题和转写文稿内容（FTS5全文索引）"""
    try:
        # Lazily populate FTS5 index if empty (first search after startup / DB reset)
        from media_tools.db.core import ensure_fts_populated

        ensure_fts_populated()

        # Sanitize user query: escape FTS5 special chars, allow prefix match with *
        safe_q = q.replace('"', '""')
        # Use prefix match (q*) for better UX
        fts_query = f'"{safe_q}"*'

        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT a.asset_id, a.creator_uid, a.title, a.video_status, a.transcript_status,
                       a.transcript_path, a.transcript_preview, a.folder_path, a.is_read, a.is_starred,
                       a.create_time, a.update_time,
                       CASE WHEN LOWER(a.title) LIKE LOWER(?) THEN 'title' ELSE 'content' END AS match_type
                FROM media_assets a
                INNER JOIN assets_fts f ON a.asset_id = f.asset_id
                WHERE assets_fts MATCH ?
                ORDER BY
                  CASE WHEN LOWER(a.title) LIKE LOWER(?) THEN 0 ELSE 1 END,
                  a.update_time DESC
                LIMIT 50
                """,
                (f"%{q}%", fts_query, f"%{q}%"),
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.exception("search_assets failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
def export_transcripts(asset_ids: list[str]):
    """批量导出转写文稿为 zip"""
    if not asset_ids:
        raise HTTPException(status_code=400, detail="No asset IDs provided")

    config = get_config()
    transcripts_dir = config.project_root / "transcripts"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        used_filenames: set[str] = set()
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
                    suffix = transcript_file.suffix or ".md"
                    stem = f"{row['title'] or row['asset_id']}"
                    # 清理文件名
                    stem = ''.join(c for c in stem if c not in '<>:"/\\|?*').strip() or str(row['asset_id'])
                    filename = f"{stem}{suffix}"
                    if filename in used_filenames:
                        filename = f"{stem}-{row['asset_id']}{suffix}"
                    used_filenames.add(filename)
                    zf.writestr(filename, transcript_file.read_bytes())

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

        if transcript_file.suffix.lower() == ".docx":
            from media_tools.pipeline.preview import extract_transcript_text

            content = extract_transcript_text(transcript_file)
        else:
            content = transcript_file.read_text(encoding="utf-8", errors="replace")
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
            # 开启事务，文件删除失败可回滚
            conn.execute("BEGIN IMMEDIATE")

            media_asset_columns = _get_table_columns(conn, "media_assets")
            source_url_select = "source_url," if "source_url" in media_asset_columns else "'' AS source_url,"
            cursor = conn.execute(
                f"SELECT creator_uid, {source_url_select} video_path, transcript_path FROM media_assets WHERE asset_id = ?",
                (asset_id,),
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Asset not found")

            creator_uid = row['creator_uid']
            source_url = row['source_url']
            video_path = row['video_path']
            transcript_name = row['transcript_path']

            config = get_config()

            # Phase 1: Delete video file (先删文件)
            if creator_uid != LOCAL_CREATOR_UID and (source_url or video_path):
                full_video_path = _resolve_asset_video_file(
                    creator_uid=creator_uid,
                    source_url=source_url,
                    video_path=video_path,
                    download_dir=config.get_download_path(),
                )
                if full_video_path and full_video_path.exists():
                    try:
                        full_video_path.unlink()
                    except OSError as e:
                        conn.rollback()
                        raise HTTPException(status_code=500, detail=f"删除视频文件失败: {full_video_path}")

            # Phase 2: Delete transcript file
            if transcript_name:
                full_transcript_path = _resolve_safe_path(config.project_root / "transcripts", transcript_name)
                if full_transcript_path and full_transcript_path.exists():
                    try:
                        full_transcript_path.unlink()
                    except OSError as e:
                        conn.rollback()
                        raise HTTPException(status_code=500, detail=f"删除转写文件失败: {full_transcript_path}")

            # Phase 3: Delete from database (后删DB)
            conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
            conn.commit()

            return {"status": "success", "message": f"Asset {asset_id} deleted successfully"}

    except HTTPException:
        raise
    except OSError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AssetMarkRequest(BaseModel):
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None

@router.patch("/{asset_id}/mark")
def mark_asset(asset_id: str, req: AssetMarkRequest):
    """标记素材为已读/收藏"""
    updates: list[str] = []
    params: list = []
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
        cursor = conn.execute(f"UPDATE media_assets SET {', '.join(updates)} WHERE asset_id = ?", params)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")
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


class BulkAssetDeleteRequest(BaseModel):
    ids: list[str]


@router.post("/bulk_delete")
def bulk_delete_assets(req: BulkAssetDeleteRequest):
    """批量删除素材（含视频与转写文件）"""
    if not req.ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")

    config = get_config()
    download_dir = config.get_download_path()
    transcripts_dir = config.project_root / "transcripts"
    failed_deletions: list[str] = []

    deleted = 0
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        media_asset_columns = _get_table_columns(conn, "media_assets")
        source_url_select = "source_url," if "source_url" in media_asset_columns else "'' AS source_url,"

        try:
            # Look up file paths in one go
            for start in range(0, len(req.ids), 500):
                chunk = req.ids[start:start + 500]
                placeholders = ",".join("?" * len(chunk))
                cursor = conn.execute(
                    f"SELECT asset_id, creator_uid, {source_url_select} video_path, transcript_path FROM media_assets WHERE asset_id IN ({placeholders})",
                    chunk,
                )
                rows = cursor.fetchall()

                # Phase 1: 删除文件
                for row in rows:
                    creator_uid = row["creator_uid"]
                    source_url = row["source_url"]
                    video_path = row["video_path"]
                    transcript_name = row["transcript_path"]
                    if creator_uid != LOCAL_CREATOR_UID and (source_url or video_path):
                        full_video_path = _resolve_asset_video_file(
                            creator_uid=creator_uid,
                            source_url=source_url,
                            video_path=video_path,
                            download_dir=download_dir,
                        )
                        if full_video_path and full_video_path.exists():
                            try:
                                full_video_path.unlink()
                            except OSError:
                                failed_deletions.append(f"video:{full_video_path}")
                    if transcript_name:
                        full_transcript_path = _resolve_safe_path(transcripts_dir, transcript_name)
                        if full_transcript_path and full_transcript_path.exists():
                            try:
                                full_transcript_path.unlink()
                            except OSError:
                                failed_deletions.append(f"transcript:{full_transcript_path}")

                # 检查是否有文件删除失败
                if failed_deletions:
                    conn.rollback()
                    raise HTTPException(status_code=500, detail=f"部分文件删除失败: {failed_deletions[:10]}")

                # Phase 2: 删除 DB 记录
                cursor = conn.execute(
                    f"DELETE FROM media_assets WHERE asset_id IN ({placeholders})",
                    chunk,
                )
                deleted += cursor.rowcount
            conn.commit()
        except HTTPException:
            raise
        except OSError:
            raise

    return {"status": "success", "deleted": deleted}


@router.post("/cleanup")
def cleanup_missing_assets():
    """清理不存在的素材（视频文件已被删除的记录）"""
    config = get_config()
    download_dir = config.get_download_path()
    transcripts_dir = config.project_root / "transcripts"

    deleted = 0
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        media_asset_columns = _get_table_columns(conn, "media_assets")
        source_url_select = "source_url," if "source_url" in media_asset_columns else "'' AS source_url,"
        # 获取所有素材
        cursor = conn.execute(f"SELECT asset_id, creator_uid, {source_url_select} video_path, transcript_path FROM media_assets")
        rows = cursor.fetchall()

        for row in rows:
            asset_id = row["asset_id"]
            creator_uid = row["creator_uid"]
            source_url = row["source_url"]
            video_path = row["video_path"]
            transcript_name = row["transcript_path"]

            video_exists = False
            transcript_exists = False

            # 检查视频文件是否存在
            if source_url or video_path:
                full_video_path = _resolve_asset_video_file(
                    creator_uid=creator_uid,
                    source_url=source_url,
                    video_path=video_path,
                    download_dir=download_dir,
                )
                if full_video_path and full_video_path.exists():
                    video_exists = True

            # 检查转写文件是否存在
            if transcript_name:
                full_transcript_path = _resolve_safe_path(transcripts_dir, transcript_name)
                if full_transcript_path and full_transcript_path.exists():
                    transcript_exists = True

            # 如果视频和转写都不存在，删除记录
            if not video_exists and not transcript_exists:
                conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
                deleted += 1

        conn.commit()
    return {"status": "success", "deleted": deleted}
