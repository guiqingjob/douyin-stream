from __future__ import annotations

import sqlite3
from pathlib import Path

from media_tools.douyin.core.config_mgr import ConfigManager, get_config
from media_tools.logger import get_logger
from media_tools.transcribe.auth_state import has_qwen_auth_state
from media_tools.web.constants import DOWNLOADS_DIR, TRANSCRIPTS_DIR
from media_tools.web.utils import format_size

logger = get_logger("web")


_DB_COUNTS_SQL = {
    "source_count": "SELECT COUNT(*) FROM creators",
    "downloaded_assets": "SELECT COUNT(*) FROM media_assets WHERE video_status = 'downloaded'",
    "pending_transcripts": "SELECT COUNT(*) FROM media_assets WHERE video_status = 'downloaded' AND COALESCE(transcript_status, 'none') != 'completed'",
    "completed_transcripts": "SELECT COUNT(*) FROM media_assets WHERE transcript_status = 'completed'",
}


def _get_db_path() -> Path:
    return get_config().get_db_path()


def _scalar(query: str) -> int:
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            value = cursor.fetchone()
            return int(value[0]) if value and value[0] is not None else 0
    except Exception:
        logger.exception("读取数据库统计失败")
        return 0


def check_douyin_auth() -> bool:
    try:
        return ConfigManager().has_cookie()
    except Exception:
        logger.exception("检查抖音认证失败")
        return False


def check_qwen_auth() -> bool:
    try:
        return has_qwen_auth_state()
    except Exception:
        logger.exception("检查 Qwen 认证失败")
        return False


def check_environment() -> bool:
    try:
        from media_tools.douyin.core.env_check import check_all

        passed, _ = check_all()
        return passed
    except Exception:
        logger.exception("环境检测失败")
        return False


def count_sources() -> int:
    return _scalar(_DB_COUNTS_SQL["source_count"])


def count_downloaded_assets() -> int:
    count = _scalar(_DB_COUNTS_SQL["downloaded_assets"])
    if count > 0:
        return count
    try:
        return sum(1 for file in DOWNLOADS_DIR.rglob("*.mp4") if file.is_file())
    except Exception:
        logger.exception("统计视频素材失败")
        return 0


def count_pending_transcripts() -> int:
    return _scalar(_DB_COUNTS_SQL["pending_transcripts"])


def count_completed_transcripts() -> int:
    count = _scalar(_DB_COUNTS_SQL["completed_transcripts"])
    if count > 0:
        return count
    try:
        return sum(1 for file in TRANSCRIPTS_DIR.rglob("*.md") if file.is_file())
    except Exception:
        logger.exception("统计文稿失败")
        return 0


def get_storage_usage_bytes() -> int:
    total_size = 0
    for directory in (DOWNLOADS_DIR, TRANSCRIPTS_DIR):
        if not directory.exists():
            continue
        try:
            total_size += sum(file.stat().st_size for file in directory.rglob("*") if file.is_file())
        except Exception:
            logger.exception("统计存储空间失败")
    return total_size


def get_storage_usage_label() -> str:
    return format_size(get_storage_usage_bytes())


def get_system_status() -> dict:
    env_ok = check_environment()
    cookie_ok = check_douyin_auth()
    qwen_ok = check_qwen_auth()
    source_count = count_sources()
    downloaded_assets = count_downloaded_assets()
    pending_transcripts = count_pending_transcripts()
    completed_transcripts = count_completed_transcripts()
    storage_total = get_storage_usage_bytes()

    if not env_ok:
        workflow_stage = "先做环境检测"
        next_page = "settings.py"
    elif not cookie_ok:
        workflow_stage = "先配置下载认证"
        next_page = "accounts.py"
    elif source_count == 0:
        workflow_stage = "先整理内容来源"
        next_page = "following_mgmt.py"
    elif downloaded_assets == 0:
        workflow_stage = "开始获取第一批素材"
        next_page = "download_center.py"
    elif not qwen_ok:
        workflow_stage = "补齐转写认证"
        next_page = "accounts.py"
    elif pending_transcripts > 0:
        workflow_stage = "继续处理待转写素材"
        next_page = "transcribe_center.py"
    else:
        workflow_stage = "系统已进入稳定工作状态"
        next_page = "asset_library.py"

    return {
        "env_ok": env_ok,
        "cookie_ok": cookie_ok,
        "qwen_ok": qwen_ok,
        "source_count": source_count,
        "downloads_count": downloaded_assets,
        "pending_transcripts": pending_transcripts,
        "transcripts_count": completed_transcripts,
        "storage_total": storage_total,
        "storage_usage": format_size(storage_total),
        "workflow_stage": workflow_stage,
        "next_page": next_page,
    }
