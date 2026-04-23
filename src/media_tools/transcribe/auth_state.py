from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
import json
import sqlite3

from media_tools.db.core import init_db
from media_tools.douyin.core.config_mgr import get_config
from media_tools.douyin.utils.auth_parser import AuthParser
from media_tools.logger import get_logger

from .config import load_config
from .runtime import as_absolute, ensure_dir

logger = get_logger(__name__)

QWEN_AUTH_PLATFORM = "qwen"
QWEN_COOKIE_DOMAIN = ".qianwen.com"
QWEN_COOKIE_CORE_KEYS = frozenset(
    {
        "tongyi_sso_ticket",
        "tongyi_sso_ticket_hash",
        "login_aliyunid_ticket",
        "login_aliyunid_ticket_sha256",
        "cookie2",
        "XSRF-TOKEN",
        "atpsida",
        "cna",
        "xlly_s",
        "aliyungf_tc",
    }
)
QWEN_COOKIE_CORE_KEYS_LOWER = frozenset(item.lower() for item in QWEN_COOKIE_CORE_KEYS)

QWEN_COOKIE_NAME_MARKERS = (
    "tongyi",
    "aliyun",
    "xsrf",
    "csrf",
    "token",
    "ticket",
    "auth",
    "sess",
    "atps",
)


@dataclass(frozen=True, slots=True)
class ResolvedQwenAuthState:
    storage_state: str | dict[str, Any]
    source: str
    auth_state_path: Path


def _normalized_path(input_path: str | Path) -> Path:
    return Path(input_path).expanduser().resolve()


def default_qwen_auth_state_path() -> Path:
    return _normalized_path(load_config().paths.auth_state_path)


def is_default_qwen_auth_state_path(auth_state_path: str | Path) -> bool:
    return _normalized_path(auth_state_path) == default_qwen_auth_state_path()


def validate_qwen_cookie_string(raw_cookie: str) -> tuple[bool, str, dict[str, str]]:
    parser = AuthParser()
    success, message, parsed = parser.validate_data(raw_cookie, "cookie", QWEN_AUTH_PLATFORM)

    normalized: dict[str, str] = {}
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            key_text = str(key).strip()
            value_text = str(value).strip()
            if key_text and value_text:
                normalized[key_text] = value_text

    return success, message, normalized


def _should_keep_qwen_cookie(cookie_name: str) -> bool:
    normalized = cookie_name.strip().lower()
    if not normalized:
        return False
    if cookie_name in QWEN_COOKIE_CORE_KEYS:
        return True
    if normalized in QWEN_COOKIE_CORE_KEYS_LOWER:
        return True
    return any(marker in normalized for marker in QWEN_COOKIE_NAME_MARKERS)


def _build_playwright_cookie(name: str, value: str) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "domain": QWEN_COOKIE_DOMAIN,
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": False,
        "sameSite": "Lax",
    }


def build_qwen_storage_state(cookie_values: Mapping[str, str]) -> dict[str, Any]:
    cookies: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_cookie(name: str, value: str) -> None:
        normalized = name.strip().lower()
        if not normalized or not value.strip() or normalized in seen:
            return
        seen.add(normalized)
        cookies.append(_build_playwright_cookie(name.strip(), value.strip()))

    for name, value in cookie_values.items():
        if _should_keep_qwen_cookie(name):
            add_cookie(name, value)

    if not cookies:
        for name, value in cookie_values.items():
            add_cookie(name, value)

    return {"cookies": cookies, "origins": []}


def build_qwen_storage_state_from_cookie_string(raw_cookie: str) -> dict[str, Any]:
    success, message, cookies = validate_qwen_cookie_string(raw_cookie)
    if not success:
        raise ValueError(message)

    state = build_qwen_storage_state(cookies)
    if not is_valid_qwen_storage_state(state):
        raise ValueError("未能从 Cookie 中构建有效的 Qwen 认证状态")
    return state


def is_valid_qwen_storage_state(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    cookies = value.get("cookies")
    if not isinstance(cookies, list) or not cookies:
        return False
    return any(
        isinstance(cookie, dict)
        and str(cookie.get("name", "")).strip()
        and str(cookie.get("value", "")).strip()
        for cookie in cookies
    )


def read_qwen_storage_state_file(auth_state_path: str | Path) -> dict[str, Any] | None:
    path = _normalized_path(auth_state_path)
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return parsed if is_valid_qwen_storage_state(parsed) else None


def load_qwen_storage_state_from_db(db_path: str | Path | None = None) -> dict[str, Any] | None:
    configured_path = db_path if db_path is not None else get_config().get_db_path()
    resolved_db_path = Path(configured_path).expanduser().resolve()
    if not resolved_db_path.exists():
        return None

    try:
        from media_tools.db.core import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT auth_data FROM auth_credentials WHERE platform = ?",
                (QWEN_AUTH_PLATFORM,),
            )
            row = cursor.fetchone()
    except sqlite3.Error:
        return None

    if not row or not row[0]:
        return None

    try:
        parsed = json.loads(str(row[0]))
    except (TypeError, ValueError, json.JSONDecodeError):
        logger.warning("Qwen 认证数据库记录不是合法 JSON，已忽略")
        return None

    return parsed if is_valid_qwen_storage_state(parsed) else None


def has_qwen_auth_state(auth_state_path: str | Path | None = None) -> bool:
    target_path = _normalized_path(auth_state_path or default_qwen_auth_state_path())
    if is_default_qwen_auth_state_path(target_path) and load_qwen_storage_state_from_db() is not None:
        return True
    return read_qwen_storage_state_file(target_path) is not None


def resolve_qwen_auth_state_for_playwright(auth_state_path: str | Path) -> ResolvedQwenAuthState:
    target_path = _normalized_path(auth_state_path)
    if is_default_qwen_auth_state_path(target_path):
        db_state = load_qwen_storage_state_from_db()
        if db_state is not None:
            return ResolvedQwenAuthState(
                storage_state=db_state,
                source="db",
                auth_state_path=target_path,
            )

    file_state = read_qwen_storage_state_file(target_path)
    if file_state is not None:
        return ResolvedQwenAuthState(
            storage_state=file_state,
            source="file",
            auth_state_path=target_path,
        )

    raise FileNotFoundError(f"auth state file does not exist or is invalid: {target_path}")


def persist_qwen_auth_state(
    state: Mapping[str, Any],
    auth_state_path: str | Path,
    *,
    sync_db: bool | None = None,
) -> Path:
    serialized_state = dict(state)
    if not is_valid_qwen_storage_state(serialized_state):
        raise ValueError("invalid Qwen storage state payload")

    target_path = _normalized_path(auth_state_path)
    ensure_dir(target_path.parent)
    target_path.write_text(
        json.dumps(serialized_state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    should_sync_db = is_default_qwen_auth_state_path(target_path) if sync_db is None else sync_db
    if should_sync_db:
        db_path = Path(get_config().get_db_path()).expanduser().resolve()
        init_db(db_path)
        from media_tools.db.core import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO auth_credentials (platform, auth_data, is_valid, last_check_time)
                VALUES (?, ?, ?, ?)
                """,
                (
                    QWEN_AUTH_PLATFORM,
                    json.dumps(serialized_state, ensure_ascii=False),
                    True,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            conn.commit()

    return target_path


def save_qwen_cookie_string(
    raw_cookie: str,
    auth_state_path: str | Path,
    *,
    sync_db: bool | None = None,
) -> dict[str, Any]:
    state = build_qwen_storage_state_from_cookie_string(raw_cookie)
    persist_qwen_auth_state(state, auth_state_path, sync_db=sync_db)
    return state
