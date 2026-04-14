from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from media_tools.transcribe.auth_state import has_qwen_auth_state, save_qwen_cookie_string, default_qwen_auth_state_path
from typing import Any, Dict

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

class QwenConfigRequest(BaseModel):
    cookie_string: str

@router.get("/")
def get_settings():
    return {
        "qwen_configured": has_qwen_auth_state()
    }

@router.post("/qwen")
def update_qwen_key(req: QwenConfigRequest):
    try:
        # Parse and save the raw cookie string
        save_qwen_cookie_string(req.cookie_string, default_qwen_auth_state_path())
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))