from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import json
import re
import uuid

from playwright.async_api import async_playwright

from .auth_state import resolve_qwen_auth_state_for_playwright
from .config import load_config
from .http import api_json
from .runtime import ensure_dir


@dataclass(frozen=True, slots=True)
class QuotaSnapshot:
    raw: Any
    used_upload: int
    total_upload: int
    remaining_upload: int
    gratis_upload: bool
    free: bool


@dataclass(frozen=True, slots=True)
class ClaimEquityResult:
    claimed: bool
    skipped: bool
    reason: str
    before_snapshot: QuotaSnapshot | None
    after_snapshot: QuotaSnapshot | None


def number_value(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed


def remaining_hours_from_snapshot(snapshot: QuotaSnapshot) -> int:
    return max(0, number_value(snapshot.remaining_upload) // 60)


def today_key() -> str:
    return datetime.now(UTC).date().isoformat()


def quota_state_path() -> Path:
    return load_config().paths.quota_state_file


def _read_quota_state() -> tuple[Path, dict[str, Any]]:
    file_path = quota_state_path()
    try:
        parsed = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return file_path, {}
    return file_path, parsed if isinstance(parsed, dict) else {}


def _write_quota_state(records: dict[str, Any]) -> Path:
    file_path = quota_state_path()
    ensure_dir(file_path.parent)
    file_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return file_path


def account_key(account_id: str) -> str:
    return account_id or "__default__"


def build_daily_record(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return {
        "consumedMinutes": number_value(source.get("consumedMinutes")),
        "lastBeforeRemaining": source.get("lastBeforeRemaining"),
        "lastAfterRemaining": source.get("lastAfterRemaining"),
        "lastEquityClaimAt": str(source.get("lastEquityClaimAt", "")),
        "lastEquityBeforeRemaining": source.get("lastEquityBeforeRemaining"),
        "lastEquityAfterRemaining": source.get("lastEquityAfterRemaining"),
        "updatedAt": str(source.get("updatedAt", "")),
    }


def merge_consumption_record(
    current_record: dict[str, Any],
    *,
    consumed_minutes: int,
    before_remaining: int,
    after_remaining: int,
    updated_at: str,
) -> dict[str, Any]:
    current_day = build_daily_record(current_record)
    return {
        **current_day,
        "consumedMinutes": number_value(current_day.get("consumedMinutes")) + max(0, number_value(consumed_minutes)),
        "lastBeforeRemaining": before_remaining,
        "lastAfterRemaining": after_remaining,
        "updatedAt": updated_at,
    }


def merge_equity_claim_record(
    current_record: dict[str, Any],
    *,
    before_remaining: int,
    after_remaining: int,
    claimed_at: str,
) -> dict[str, Any]:
    current_day = build_daily_record(current_record)
    return {
        **current_day,
        "lastEquityClaimAt": claimed_at,
        "lastEquityBeforeRemaining": before_remaining,
        "lastEquityAfterRemaining": after_remaining,
        "updatedAt": claimed_at,
    }


async def get_quota_snapshot(
    *,
    auth_state_path: str | Path,
    referer: str = "https://www.qianwen.com/discover/audioread",
) -> QuotaSnapshot:
    resolved = resolve_qwen_auth_state_for_playwright(auth_state_path)

    async with async_playwright() as playwright:
        api = await playwright.request.new_context(storage_state=resolved.storage_state)  # type: ignore[arg-type]
        try:
            quota_json = await api_json(
                api,
                "https://api.qianwen.com/growth/user/benefit/base",
                {"requestId": str(uuid.uuid4())},
                {
                    "referer": referer,
                    "platform": "QIANWEN",
                    "request-id": str(uuid.uuid4()),
                    "bx-v": "2.5.36",
                },
            )
        finally:
            await api.dispose()

    data = quota_json.get("data", []) if isinstance(quota_json, dict) else []
    tingwu_benefit = {}
    if isinstance(data, list):
        tingwu_benefit = next(
            (item for item in data if isinstance(item, dict) and item.get("benefitType") == "TINGWU_TRANSCRIPTION_DURATION"),
            {},
        )

    if not tingwu_benefit:
        return QuotaSnapshot(
            raw=quota_json,
            used_upload=0,
            total_upload=0,
            remaining_upload=0,
            gratis_upload=False,
            free=False,
        )

    used_hours = number_value(tingwu_benefit.get("usageQuota"))
    remaining_hours = number_value(tingwu_benefit.get("remainingQuota"))
    total_hours = used_hours + remaining_hours

    used_minutes = used_hours * 60
    remaining_minutes = remaining_hours * 60
    total_minutes = total_hours * 60

    total_quota_str = str(tingwu_benefit.get("totalQuotaAndUnit", ""))
    total_match = re.search(r"共(\d+)小时(\d+)分钟", total_quota_str)
    if total_match:
        total_minutes = int(total_match.group(1)) * 60 + int(total_match.group(2))

    return QuotaSnapshot(
        raw=quota_json,
        used_upload=used_minutes,
        total_upload=total_minutes,
        remaining_upload=remaining_minutes,
        gratis_upload=False,
        free=bool(remaining_hours > 0),
    )


def record_quota_consumption(
    *,
    account_id: str,
    consumed_minutes: int,
    before_snapshot: QuotaSnapshot,
    after_snapshot: QuotaSnapshot,
) -> None:
    minutes = max(0, number_value(consumed_minutes))
    _, records = _read_quota_state()
    key = account_key(account_id)
    day = today_key()
    account_record = records.get(key, {})
    account_record[day] = merge_consumption_record(
        account_record.get(day, {}),
        consumed_minutes=minutes,
        before_remaining=before_snapshot.remaining_upload,
        after_remaining=after_snapshot.remaining_upload,
        updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    records[key] = account_record
    _write_quota_state(records)


def get_daily_quota_record(account_id: str) -> dict[str, Any]:
    _, records = _read_quota_state()
    return build_daily_record(records.get(account_key(account_id), {}).get(today_key()))


async def visit_equity_page(auth_state_path: str | Path) -> None:
    resolved = resolve_qwen_auth_state_for_playwright(auth_state_path)

    async with async_playwright() as playwright:
        # 修复：尝试使用Chrome，如果不可用则回退到默认浏览器
        try:
            browser = await playwright.chromium.launch(channel="chrome", headless=True)
        except (RuntimeError, OSError):
            # Chrome不可用时回退到默认浏览器
            browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(storage_state=resolved.storage_state)  # type: ignore[arg-type]
            page = await context.new_page()
            await page.goto("https://www.qianwen.com/equity", wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except RuntimeError:
                pass
            await page.wait_for_timeout(3000)
            await context.close()
        finally:
            await browser.close()


def has_claimed_equity_today(account_id: str) -> bool:
    daily = get_daily_quota_record(account_id)
    return bool(daily.get("lastEquityClaimAt"))


def _write_equity_claim_record(
    *,
    account_id: str,
    before_snapshot: QuotaSnapshot,
    after_snapshot: QuotaSnapshot,
) -> None:
    _, records = _read_quota_state()
    key = account_key(account_id)
    day = today_key()
    account_record = records.get(key, {})
    claimed_at = datetime.now(UTC).isoformat(timespec="seconds")
    account_record[day] = merge_equity_claim_record(
        account_record.get(day, {}),
        before_remaining=before_snapshot.remaining_upload,
        after_remaining=after_snapshot.remaining_upload,
        claimed_at=claimed_at,
    )
    records[key] = account_record
    _write_quota_state(records)


async def claim_equity_quota(
    *,
    account_id: str,
    auth_state_path: str | Path,
    force: bool = False,
) -> ClaimEquityResult:
    if not force and has_claimed_equity_today(account_id):
        return ClaimEquityResult(
            claimed=False,
            skipped=True,
            reason="already-claimed-today",
            before_snapshot=None,
            after_snapshot=None,
        )

    before_snapshot = await get_quota_snapshot(
        auth_state_path=auth_state_path,
        referer="https://www.qianwen.com/equity",
    )
    await visit_equity_page(auth_state_path)
    after_snapshot = await get_quota_snapshot(
        auth_state_path=auth_state_path,
        referer="https://www.qianwen.com/equity",
    )
    _write_equity_claim_record(
        account_id=account_id,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    return ClaimEquityResult(
        claimed=True,
        skipped=False,
        reason="",
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
