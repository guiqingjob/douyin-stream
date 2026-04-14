from fastapi import APIRouter, Query, HTTPException
from media_tools.douyin.core.config_mgr import get_config
from typing import Optional
import sqlite3
import os
from pathlib import Path

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

def get_db_connection():
    db_path = get_config().get_db_path()
    return sqlite3.connect(db_path)

@router.get("/")
def list_assets(creator_uid: Optional[str] = Query(None)):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            if creator_uid:
                cursor = conn.execute(
                    "SELECT asset_id, creator_uid, title, video_status, transcript_status, transcript_path FROM media_assets WHERE creator_uid = ?", 
                    (creator_uid,)
                )
            else:
                cursor = conn.execute("SELECT asset_id, creator_uid, title, video_status, transcript_status, transcript_path FROM media_assets")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

@router.get("/{asset_id}/transcript")
def get_transcript(asset_id: str):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT transcript_path FROM media_assets WHERE asset_id = ?", (asset_id,))
            row = cursor.fetchone()
            
            if not row or not row['transcript_path']:
                raise HTTPException(status_code=404, detail="Transcript not found in database")
                
            transcript_name = row['transcript_path']
            # Construct the full path
            # Pipeline config defaults to "./transcripts/" relative to project root
            config = get_config()
            transcripts_dir = config.project_root / "transcripts"
            transcript_file = transcripts_dir / transcript_name
            
            if not transcript_file.exists():
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
                full_video_path = config.get_download_path() / video_path
                if full_video_path.exists():
                    try:
                        full_video_path.unlink()
                    except Exception as e:
                        print(f"Failed to delete video file {full_video_path}: {e}")
                        
            # Delete transcript file
            if transcript_name:
                full_transcript_path = config.project_root / "transcripts" / transcript_name
                if full_transcript_path.exists():
                    try:
                        full_transcript_path.unlink()
                    except Exception as e:
                        print(f"Failed to delete transcript file {full_transcript_path}: {e}")
            
            # Delete from database
            conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
            conn.commit()
            
            return {"status": "success", "message": f"Asset {asset_id} deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))