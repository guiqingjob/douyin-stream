from fastapi import APIRouter, Query
from media_tools.douyin.core.config_mgr import get_config
from typing import Optional
import sqlite3

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