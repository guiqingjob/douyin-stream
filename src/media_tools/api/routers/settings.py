import sqlite3
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from media_tools.transcribe.auth_state import has_qwen_auth_state, save_qwen_cookie_string, default_qwen_auth_state_path
from media_tools.douyin.core.config_mgr import get_config

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

class QwenConfigRequest(BaseModel):
    cookie_string: str

class DouyinAccountRequest(BaseModel):
    cookie_string: str

class GlobalSettingsRequest(BaseModel):
    concurrency: int
    auto_delete: bool

def _get_db_conn():
    db_path = get_config().get_db_path()
    conn = sqlite3.connect(str(db_path))
    # ensure tables exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Accounts_Pool (
            account_id TEXT PRIMARY KEY,
            platform TEXT,
            cookie_data TEXT,
            status TEXT DEFAULT 'active',
            last_used TIMESTAMP,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS SystemSettings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    return conn

@router.get("/")
def get_settings():
    conn = _get_db_conn()
    cursor = conn.cursor()
    
    # Get douyin accounts
    cursor.execute("SELECT account_id, status, last_used FROM Accounts_Pool WHERE platform='douyin'")
    accounts = [{"id": row[0], "status": row[1], "last_used": row[2]} for row in cursor.fetchall()]
    
    # Get global settings
    cursor.execute("SELECT key, value FROM SystemSettings")
    settings_rows = cursor.fetchall()
    settings_dict = {row[0]: row[1] for row in settings_rows}
    
    concurrency = int(settings_dict.get("concurrency", 3))
    auto_delete = settings_dict.get("auto_delete", "false") == "true"
    
    conn.close()
    
    return {
        "qwen_configured": has_qwen_auth_state(),
        "douyin_accounts": accounts,
        "global_settings": {
            "concurrency": concurrency,
            "auto_delete": auto_delete
        }
    }

@router.post("/douyin")
def add_douyin_account(req: DouyinAccountRequest):
    try:
        conn = _get_db_conn()
        account_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO Accounts_Pool (account_id, platform, cookie_data) VALUES (?, ?, ?)",
            (account_id, "douyin", req.cookie_string)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "account_id": account_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/douyin/{account_id}")
def delete_douyin_account(account_id: str):
    try:
        conn = _get_db_conn()
        conn.execute("DELETE FROM Accounts_Pool WHERE account_id=?", (account_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/global")
def update_global_settings(req: GlobalSettingsRequest):
    try:
        conn = _get_db_conn()
        conn.execute("INSERT OR REPLACE INTO SystemSettings (key, value) VALUES (?, ?)", ("concurrency", str(req.concurrency)))
        conn.execute("INSERT OR REPLACE INTO SystemSettings (key, value) VALUES (?, ?)", ("auto_delete", "true" if req.auto_delete else "false"))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/qwen")
def update_qwen_key(req: QwenConfigRequest):
    try:
        # Parse and save the raw cookie string
        save_qwen_cookie_string(req.cookie_string, default_qwen_auth_state_path())
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))