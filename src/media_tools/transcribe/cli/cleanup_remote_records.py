from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from ..auth_state import resolve_qwen_auth_state_for_playwright
from ..errors import InputValidationError
from ..flow import delete_record
from ..http import api_json
from ..runtime import as_absolute, enable_live_output, ensure_dir, load_dotenv
from .common import command_parser


def build_parser() -> argparse.ArgumentParser:
    parser = command_parser(
        "cleanup remote-records",
        "Delete remote Qwen records referenced by local export metadata.",
    )
    parser.add_argument("--auth-state", default=".auth/qwen-storage-state.json")
    parser.add_argument(
        "--metadata-file",
        action="append",
        default=[],
        help="Optional explicit metadata sidecar path. Repeat to include multiple files.",
    )
    parser.add_argument(
        "--results-dir",
        default="downloads",
        help="Directory scanned recursively for *.meta.json files when --metadata-file is not enough.",
    )
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def discover_metadata_files(explicit_files: list[str], results_dir: str) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists() or not resolved.is_file():
            return
        seen.add(resolved)
        discovered.append(resolved)

    for raw in explicit_files:
        add(as_absolute(raw))

    root = as_absolute(results_dir)
    if root.exists():
        for path in sorted(root.rglob("*.meta.json")):
            add(path)

    return discovered


def load_record_ids(metadata_files: list[Path]) -> set[str]:
    record_ids: set[str] = set()
    for path in metadata_files:
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(parsed, dict):
            continue
        for key in ("record_id", "recordId"):
            record_id = str(parsed.get(key, "")).strip()
            if record_id:
                record_ids.add(record_id)
    return record_ids


async def fetch_all_records(api: Any, page_size: int) -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    seen_batch_ids: set[str] = set()
    page_no = 1
    while True:
        payload = {
            "status": [10, 20, 30, 40, 41],
            "fileTypes": [],
            "beginTime": "",
            "mediaType": "",
            "endTime": "",
            "showName": "",
            "read": "",
            "lang": "",
            "shareUserId": "",
            "pageNo": page_no,
            "pageSize": page_size,
            "recordSources": ["chat", "zhiwen", "tingwu"],
            "taskTypes": ["local", "net_source", "doc_read", "url_read", "paper_read", "book_read", "doc_convert"],
            "terminal": "web",
            "module": "uploadhistory",
        }
        response = await api_json(api, "https://api.qianwen.com/assistant/api/record/list/poll?c=tongyi-web", payload)
        batches = response.get("data", {}).get("batchRecord", [])
        if not batches:
            break
        before = len(all_records)
        for batch in batches:
            batch_id = str(batch.get("batchId", ""))
            if batch_id and batch_id in seen_batch_ids:
                continue
            if batch_id:
                seen_batch_ids.add(batch_id)
            all_records.extend(batch.get("recordList", []))
        if len(all_records) == before:
            break
        page_no += 1
    return all_records


async def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    enable_live_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    auth_state_path = as_absolute(args.auth_state)
    try:
        resolved_auth = resolve_qwen_auth_state_for_playwright(auth_state_path)
    except FileNotFoundError as exc:
        raise InputValidationError(f"{exc}. Run `qwen-transcribe auth` first.") from exc

    metadata_files = discover_metadata_files(args.metadata_file, args.results_dir)
    record_ids = load_record_ids(metadata_files)
    if not record_ids:
        print("no record ids found in local metadata sidecars")
        return 0

    async with async_playwright() as p:
        api = await p.request.new_context(storage_state=resolved_auth.storage_state)
        try:
            records = await fetch_all_records(api, args.page_size)
            matched = [record for record in records if str(record.get("recordId", "")).strip() in record_ids]
            summary = {
                "metadata_files": len(metadata_files),
                "record_ids": len(record_ids),
                "remote_records_scanned": len(records),
                "matched_remote_records": len(matched),
                "dry_run": args.dry_run,
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            if args.dry_run:
                for row in matched[:100]:
                    print(json.dumps({"recordTitle": row.get("recordTitle"), "recordId": row.get("recordId")}, ensure_ascii=False))
                return 0

            deleted = 0
            failed: list[dict[str, str]] = []
            for row in matched:
                record_id = str(row.get("recordId", "")).strip()
                if not record_id:
                    continue
                ok = await delete_record(api, [record_id])
                if ok:
                    deleted += 1
                else:
                    failed.append({"recordTitle": str(row.get("recordTitle", "")), "recordId": record_id})

            log_path = as_absolute(Path(args.results_dir) / "cleanup-remote-records-log.json")
            ensure_dir(log_path.parent)
            payload = {
                "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "deleted_count": deleted,
                "failed_count": len(failed),
                "failed_records": failed,
            }
            log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            print(f"cleanup log saved: {log_path}")
            return 0 if not failed else 1
        finally:
            await api.dispose()


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
