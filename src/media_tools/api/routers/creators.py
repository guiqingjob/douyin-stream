from fastapi import APIRouter, HTTPException
from media_tools.douyin.core.config_mgr import get_config
import sqlite3
import shutil

router = APIRouter(prefix="/api/v1/creators", tags=["creators"])

def get_db_connection():
    db_path = get_config().get_db_path()
    return sqlite3.connect(db_path)

@router.get("/")
def list_creators():
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT uid, nickname, sec_user_id, sync_status FROM creators")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

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
            
            # Also try to delete the creator's download folder if it exists
            # Usually it's named after the nickname or uid
            for folder_name in [nickname, uid]:
                if folder_name:
                    creator_dir = config.get_download_path() / folder_name
                    if creator_dir.exists() and creator_dir.is_dir():
                        try:
                            shutil.rmtree(creator_dir)
                        except Exception as e:
                            print(f"Failed to delete creator directory {creator_dir}: {e}")
            
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