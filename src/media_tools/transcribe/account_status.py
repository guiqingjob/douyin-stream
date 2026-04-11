from __future__ import annotations

from pathlib import Path
from typing import Any

from .accounts import load_accounts_config, resolve_auth_state_path
from .config import load_config
from .quota import get_daily_quota_record, get_quota_snapshot


def to_number(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed


def recommend_action(*, auth_exists: bool, quota: Any, quota_error: str, daily: dict[str, Any]) -> str:
    if not auth_exists:
        return "need-auth"
    if quota_error:
        return "quota-check-failed"

    low_quota_threshold = load_config().status_low_quota_minutes
    remaining_upload = to_number(getattr(quota, "remaining_upload", 0))

    if not daily.get("lastEquityClaimAt"):
        if remaining_upload <= low_quota_threshold:
            return "claim-today"
        return "ready"

    if remaining_upload <= low_quota_threshold:
        return "quota-low"

    return "ready"


def resolve_status_targets():
    _, accounts = load_accounts_config()
    if not accounts:
        return [resolve_auth_state_path(account_id="")]
    return [resolve_auth_state_path(account_id=account.id) for account in accounts]


async def collect_account_statuses() -> list[dict[str, Any]]:
    targets = resolve_status_targets()
    rows: list[dict[str, Any]] = []

    for account in targets:
        auth_exists = Path(account.auth_state_path).exists()
        daily = get_daily_quota_record(account.account_id)

        quota = None
        quota_error = ""
        if auth_exists:
            try:
                quota = await get_quota_snapshot(
                    auth_state_path=account.auth_state_path,
                    referer="https://www.qianwen.com/equity",
                )
            except Exception as error:
                quota_error = str(error)

        rows.append(
            {
                "accountId": account.account_id or "default",
                "accountLabel": account.account_label or "default",
                "authStatePath": str(account.auth_state_path),
                "authExists": auth_exists,
                "quota": quota,
                "quotaError": quota_error,
                "daily": daily,
                "action": recommend_action(
                    auth_exists=auth_exists,
                    quota=quota,
                    quota_error=quota_error,
                    daily=daily,
                ),
                "note": "missing storageState" if not auth_exists else (f"quota failed: {quota_error}" if quota_error else "ok"),
            }
        )

    return rows
