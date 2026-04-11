from __future__ import annotations

import argparse
import asyncio

from ..config import load_config
from ..runtime import enable_live_output, load_dotenv
from .common import (
    add_flow_execution_arguments,
    command_parser,
    format_bool,
    print_account_pool,
    resolve_flow_cli_config,
    validate_source_file,
)
from .flow_execution import execute_flow_with_fallback


def build_parser() -> argparse.ArgumentParser:
    parser = command_parser("run", "Run the verified Qwen API flow for one media file.")
    parser.add_argument("file_path", nargs="?", help="Local media file path")
    add_flow_execution_arguments(parser)
    return parser


async def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    enable_live_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    target_file = args.file_path or load_config().flow_file
    if not target_file:
        parser.error("Provide a media file path or set QWEN_FLOW_FILE in .env")
    file_path = validate_source_file(target_file)
    try:
        cli_config = resolve_flow_cli_config(args)
    except Exception as error:
        parser.error(str(error))

    print("")
    print("=== Run Configuration ===")
    print(f"File: {file_path}")
    print(f"Format: {cli_config.export_config.label}")
    print(f"Output dir: {cli_config.output_dir}")
    print(f"Delete remote: {format_bool(cli_config.should_delete)}")
    print(f"Export concurrency: {cli_config.export_concurrency}")
    print("=========================")
    print("")

    print_account_pool(cli_config.execution)

    outcome = await execute_flow_with_fallback(
        source_path=file_path,
        cli_config=cli_config,
        announce_accounts=True,
    )
    completed_result = outcome.flow_result

    print("")
    print("=== Run Summary ===")
    print(f"Source: {file_path.name}")
    print(f"Export path: {completed_result.export_path}")
    print(f"Metadata path: {outcome.metadata_path}")
    print(f"Record ID: {completed_result.record_id}")
    print(f"Remote deleted: {format_bool(completed_result.remote_deleted)}")
    print("")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
