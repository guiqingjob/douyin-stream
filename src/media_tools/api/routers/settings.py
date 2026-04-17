import logging
import sqlite3
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from media_tools.transcribe.auth_state import has_qwen_auth_state, save_qwen_cookie_string, default_qwen_auth_state_path
from media_tools.transcribe.db_account_pool import build_qwen_auth_state_path_for_account
from media_tools.douyin.core.config_mgr import get_config
from media_tools.db.core import get_db_connection

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
logger = logging.getLogger(__name__)

class QwenConfigRequest(BaseModel):
    cookie_string: str

class QwenAccountRequest(BaseModel):
    cookie_string: str
    remark: str = ""

class QwenCookieUpdateRequest(BaseModel):
    cookie_string: str

class DouyinAccountRequest(BaseModel):
    cookie_string: str
    remark: str = ""

class BilibiliAccountRequest(BaseModel):
    cookie_string: str
    remark: str = ""

class GlobalSettingsRequest(BaseModel):
    concurrency: int
    auto_delete: bool
    auto_transcribe: bool

class RemarkRequest(BaseModel):
    remark: str

@router.get("/")
def get_settings():
    config = get_config()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get douyin accounts
        cursor.execute("SELECT account_id, status, last_used, remark, create_time FROM Accounts_Pool WHERE platform='douyin'")
        accounts = [{"id": row[0], "status": row[1], "last_used": row[2], "remark": row[3] or "", "create_time": row[4] or ""} for row in cursor.fetchall()]

        # Get qwen accounts
        cursor.execute("SELECT account_id, status, last_used, remark, create_time FROM Accounts_Pool WHERE platform='qwen'")
        qwen_accounts = [{"id": row[0], "status": row[1], "last_used": row[2], "remark": row[3] or "", "create_time": row[4] or ""} for row in cursor.fetchall()]

        # Get bilibili accounts
        cursor.execute("SELECT account_id, status, last_used, remark, create_time FROM Accounts_Pool WHERE platform='bilibili'")
        bilibili_accounts = [{"id": row[0], "status": row[1], "last_used": row[2], "remark": row[3] or "", "create_time": row[4] or ""} for row in cursor.fetchall()]

        # Get global settings
        cursor.execute("SELECT key, value FROM SystemSettings")
        settings_rows = cursor.fetchall()
        settings_dict = {row[0]: row[1] for row in settings_rows}

    concurrency = int(settings_dict.get("concurrency", 3))
    auto_delete = config.is_auto_delete_video()
    auto_transcribe = config.is_auto_transcribe()
    douyin_accounts_count = len(accounts)
    douyin_primary_configured = config.has_cookie()
    douyin_cookie_source = "pool" if douyin_accounts_count > 0 else ("config" if douyin_primary_configured else "none")
    qwen_configured = has_qwen_auth_state()
    qwen_accounts_count = len(qwen_accounts)

    return {
        "qwen_configured": qwen_configured,
        "douyin_accounts": accounts,
        "qwen_accounts": qwen_accounts,
        "bilibili_accounts": bilibili_accounts,
        "global_settings": {
            "concurrency": concurrency,
            "auto_delete": auto_delete,
            "auto_transcribe": auto_transcribe,
        },
        "status_summary": {
            "qwen_ready": qwen_configured or qwen_accounts_count > 0,
            "douyin_ready": douyin_primary_configured or douyin_accounts_count > 0,
            "douyin_accounts_count": douyin_accounts_count,
            "douyin_primary_configured": douyin_primary_configured,
            "douyin_cookie_source": douyin_cookie_source,
            "qwen_accounts_count": qwen_accounts_count,
            "bilibili_accounts_count": len(bilibili_accounts),
            "can_download": douyin_primary_configured or douyin_accounts_count > 0,
            "can_transcribe": qwen_configured or qwen_accounts_count > 0,
            "can_run_pipeline": (douyin_primary_configured or douyin_accounts_count > 0) and (qwen_configured or qwen_accounts_count > 0),
        }
    }

@router.post("/douyin")
def add_douyin_account(req: DouyinAccountRequest):
    try:
        account_id = str(uuid.uuid4())
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO Accounts_Pool (account_id, platform, cookie_data, remark) VALUES (?, ?, ?, ?)",
                (account_id, "douyin", req.cookie_string, req.remark)
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

@router.put("/douyin/{account_id}/remark")
def update_douyin_account_remark(account_id: str, req: RemarkRequest):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Accounts_Pool SET remark=? WHERE account_id=?", (req.remark, account_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Account not found")
            conn.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bilibili/accounts")
def add_bilibili_account(req: BilibiliAccountRequest):
    try:
        account_id = str(uuid.uuid4())
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO Accounts_Pool (account_id, platform, cookie_data, remark) VALUES (?, ?, ?, ?)",
                (account_id, "bilibili", req.cookie_string, req.remark),
            )
            conn.commit()
        return {"status": "success", "account_id": account_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/bilibili/accounts/{account_id}")
def delete_bilibili_account(account_id: str):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM Accounts_Pool WHERE account_id=? AND platform='bilibili'", (account_id,))
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/bilibili/accounts/{account_id}/remark")
def update_bilibili_account_remark(account_id: str, req: RemarkRequest):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Accounts_Pool SET remark=? WHERE account_id=? AND platform='bilibili'",
                (req.remark, account_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Account not found")
            conn.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/qwen/status")
async def get_qwen_status():
    """获取 Qwen 转写余额和今日用量"""
    try:
        from media_tools.transcribe.account_status import collect_account_statuses
        statuses = await collect_account_statuses()
        return {"status": "success", "accounts": statuses}
    except Exception as e:
        return {"status": "unavailable", "message": str(e), "accounts": []}

@router.post("/qwen/claim")
async def claim_qwen_quota_endpoint():
    """手动触发领取每日 Qwen 额度"""
    try:
        from media_tools.transcribe.quota import claim_equity_quota, has_claimed_equity_today
        from media_tools.transcribe.account_status import resolve_status_targets

        targets = resolve_status_targets()
        results = []
        for target in targets:
            account_id = target.account_id or ""
            if has_claimed_equity_today(account_id):
                results.append({"accountId": account_id or "default", "status": "already_claimed", "message": "今日已领取"})
                continue
            result = await claim_equity_quota(
                account_id=account_id,
                auth_state_path=target.auth_state_path,
            )
            results.append({
                "accountId": account_id or "default",
                "status": "claimed" if result.claimed else "skipped",
                "reason": result.reason,
            })
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        save_qwen_cookie_string(req.cookie_string, default_qwen_auth_state_path())
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/qwen/accounts")
def add_qwen_account(req: QwenAccountRequest):
    try:
        account_id = str(uuid.uuid4())
        auth_state_path = build_qwen_auth_state_path_for_account(account_id)
        save_qwen_cookie_string(req.cookie_string, auth_state_path, sync_db=False)
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO Accounts_Pool (account_id, platform, cookie_data, remark, auth_state_path) VALUES (?, ?, ?, ?, ?)",
                (account_id, "qwen", req.cookie_string, req.remark, str(auth_state_path)),
            )
            conn.commit()
        return {"status": "success", "account_id": account_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/qwen/accounts/{account_id}/cookie")
def update_qwen_account_cookie(account_id: str, req: QwenCookieUpdateRequest):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT auth_state_path FROM Accounts_Pool WHERE account_id=? AND platform='qwen'",
                (account_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Account not found")

            existing_path = str(row[0] or "")
            auth_state_path = Path(existing_path) if existing_path.strip() else build_qwen_auth_state_path_for_account(account_id)

            save_qwen_cookie_string(req.cookie_string, auth_state_path, sync_db=False)

            cursor.execute(
                "UPDATE Accounts_Pool SET cookie_data=?, status='active', auth_state_path=? WHERE account_id=? AND platform='qwen'",
                (req.cookie_string, str(auth_state_path), account_id),
            )
            conn.commit()

        return {"status": "success", "account_id": account_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/qwen/accounts/{account_id}")
def delete_qwen_account(account_id: str):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM Accounts_Pool WHERE account_id=? AND platform='qwen'", (account_id,))
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/qwen/accounts/{account_id}/remark")
def update_qwen_account_remark(account_id: str, req: RemarkRequest):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Accounts_Pool SET remark=? WHERE account_id=? AND platform='qwen'", (req.remark, account_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Account not found")
            conn.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
