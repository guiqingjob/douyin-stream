import sqlite3
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from media_tools.transcribe.auth_state import has_qwen_auth_state, save_qwen_cookie_string, default_qwen_auth_state_path
from media_tools.douyin.core.config_mgr import get_config
from media_tools.db.core import get_db_connection

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

class QwenConfigRequest(BaseModel):
    cookie_string: str

class DouyinAccountRequest(BaseModel):
    cookie_string: str

class GlobalSettingsRequest(BaseModel):
    concurrency: int
    auto_delete: bool
    auto_transcribe: bool

@router.get("/")
def get_settings():
    config = get_config()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get douyin accounts
        cursor.execute("SELECT account_id, status, last_used FROM Accounts_Pool WHERE platform='douyin'")
        accounts = [{"id": row[0], "status": row[1], "last_used": row[2]} for row in cursor.fetchall()]

        # Get global settings
        cursor.execute("SELECT key, value FROM SystemSettings")
        settings_rows = cursor.fetchall()
        settings_dict = {row[0]: row[1] for row in settings_rows}

    concurrency = int(settings_dict.get("concurrency", 3))
    auto_delete = config.is_auto_delete_video()
    auto_transcribe = config.is_auto_transcribe()
    douyin_accounts_count = len(accounts)
    douyin_primary_configured = config.has_cookie()
    douyin_cookie_source = "config" if douyin_primary_configured else ("pool" if douyin_accounts_count > 0 else "none")
    qwen_configured = has_qwen_auth_state()

    return {
        "qwen_configured": qwen_configured,
        "douyin_accounts": accounts,
        "global_settings": {
            "concurrency": concurrency,
            "auto_delete": auto_delete,
            "auto_transcribe": auto_transcribe,
        },
        "status_summary": {
            "qwen_ready": qwen_configured,
            "douyin_ready": douyin_primary_configured or douyin_accounts_count > 0,
            "douyin_accounts_count": douyin_accounts_count,
            "douyin_primary_configured": douyin_primary_configured,
            "douyin_cookie_source": douyin_cookie_source,
            "can_download": douyin_primary_configured or douyin_accounts_count > 0,
            "can_transcribe": qwen_configured,
            "can_run_pipeline": (douyin_primary_configured or douyin_accounts_count > 0) and qwen_configured,
        }
    }

@router.post("/douyin")
def add_douyin_account(req: DouyinAccountRequest):
    try:
        account_id = str(uuid.uuid4())
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO Accounts_Pool (account_id, platform, cookie_data) VALUES (?, ?, ?)",
                (account_id, "douyin", req.cookie_string)
            )
            conn.commit()
        return {"status": "success", "account_id": account_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/douyin/{account_id}")
def delete_douyin_account(account_id: str):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM Accounts_Pool WHERE account_id=?", (account_id,))
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/global")
def update_global_settings(req: GlobalSettingsRequest):
    try:
        config = get_config()
        config.set("auto_delete_video", req.auto_delete)
        config.set("auto_transcribe", req.auto_transcribe)
        config.save()

        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO SystemSettings (key, value) VALUES (?, ?)", ("concurrency", str(req.concurrency)))
            conn.execute("INSERT OR REPLACE INTO SystemSettings (key, value) VALUES (?, ?)", ("auto_delete", "true" if req.auto_delete else "false"))
            conn.execute("INSERT OR REPLACE INTO SystemSettings (key, value) VALUES (?, ?)", ("auto_transcribe", "true" if req.auto_transcribe else "false"))
            conn.commit()
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
