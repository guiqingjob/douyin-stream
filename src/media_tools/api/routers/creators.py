from fastapi import APIRouter
from media_tools.douyin.core.config_mgr import get_config
import sqlite3

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