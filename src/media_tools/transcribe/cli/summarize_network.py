from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import command_parser


def build_parser() -> argparse.ArgumentParser:
    parser = command_parser("summarize", "Summarize captured Qwen network JSONL logs.")
    parser.add_argument("files", nargs="+", help="One or more JSONL files produced by qwen-transcribe capture")
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    interesting_keywords = ("upload", "task", "transcript", "export", "oss", "record", "audio", "video", "docx")
    seen: dict[tuple[str, str], dict[str, object]] = {}

    for raw_path in args.files:
        path = Path(raw_path)
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                entry = json.loads(raw_line)
            except Exception:
                continue
            if entry.get("kind") != "response" or not entry.get("url"):
                continue
            from urllib.parse import urlparse

            parsed = urlparse(str(entry["url"]))
            key = (str(entry.get("method", "")), parsed.path)
            current = seen.setdefault(
                key,
                {
                    "method": key[0],
                    "path": parsed.path,
                    "count": 0,
                    "statuses": set(),
                    "types": set(),
                    "interesting": any(item in parsed.path.lower() for item in interesting_keywords),
                },
            )
            current["count"] = int(current["count"]) + 1
            current["statuses"].add(str(entry.get("status", "")))
            current["types"].add(str(entry.get("resourceType", "")))

    rows = sorted(
        seen.values(),
        key=lambda item: (not bool(item["interesting"]), -int(item["count"]), str(item["path"])),
    )
    for row in rows:
        marker = "*" if row["interesting"] else " "
        statuses = ",".join(sorted(row["statuses"]))
        resource_types = ",".join(sorted(row["types"]))
        print(
            f"{marker} {row['method']} {row['path']} count={row['count']} "
            f"status={statuses} type={resource_types}"
        )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
