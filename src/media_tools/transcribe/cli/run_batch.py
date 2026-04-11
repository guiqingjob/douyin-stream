from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from ..runtime import as_absolute, enable_live_output, load_dotenv
from . import rich_ui
from .common import (
    add_flow_execution_arguments,
    chunk_paths,
    collect_batch_sources,
    command_parser,
    ensure_auth_state_exists,
    format_bool,
    print_account_pool,
    print_selected_account,
    resolve_flow_cli_config,
)
from .flow_execution import execute_flow_once


def build_parser() -> argparse.ArgumentParser:
    parser = command_parser("batch", "Batch-process local media files through the Qwen API flow.")
    parser.add_argument("inputs", nargs="+", help="One or more local media files or directories")
    add_flow_execution_arguments(parser)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("QWEN_CONCURRENCY", "1")),
        help="Number of files to process in parallel (default: %(default)s)",
    )
    parser.add_argument(
        "--pattern",
        default="*.mp4",
        help="Glob pattern used when an input is a directory (default: %(default)s)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan directories for matching files",
    )
    parser.add_argument(
        "--group-size",
        type=int,
        default=10,
        help="How many files to process per batch group before moving to the next group (default: %(default)s)",
    )
    return parser


async def _process_file(
    *,
    file_path: str,
    index: int,
    total: int,
    account,
    cli_config,
) -> dict[str, object]:
    absolute_path = as_absolute(file_path)
    file_name = absolute_path.name
    print(f"\n[{index + 1}/{total}] Processing: {file_name}")
    print_selected_account(account)

    try:
        ensure_auth_state_exists(account)
        outcome = await execute_flow_once(
            source_path=absolute_path,
            account=account,
            cli_config=cli_config,
        )
        print(f"[{index + 1}/{total}] Completed: {file_name}")
        print(f"[{index + 1}/{total}] Exported: {outcome.flow_result.export_path}")
        print(f"[{index + 1}/{total}] Metadata: {outcome.metadata_path}")
        return {
            "success": True,
            "file_path": str(absolute_path),
            "export_path": str(outcome.flow_result.export_path),
            "metadata_path": str(outcome.metadata_path),
        }
    except Exception as error:
        print(f"[{index + 1}/{total}] Failed: {file_name} - {error}")
        return {"success": False, "file_path": str(absolute_path), "error": str(error)}


async def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    enable_live_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.concurrency <= 0:
        parser.error("--concurrency must be a positive integer")
    source_files = collect_batch_sources(args.inputs, pattern=args.pattern, recursive=args.recursive)
    grouped_files = chunk_paths(source_files, args.group_size)
    try:
        cli_config = resolve_flow_cli_config(args)
    except Exception as error:
        parser.error(str(error))

    print("\n=== Batch Configuration ===")
    config_content = (
        f"[bold]Files:[/bold] {len(source_files)}\n"
        f"[bold]Concurrency:[/bold] {args.concurrency}\n"
        f"[bold]Group size:[/bold] {args.group_size}\n"
        f"[bold]Groups:[/bold] {len(grouped_files)}\n"
        f"[bold]Pattern:[/bold] {args.pattern}\n"
        f"[bold]Recursive:[/bold] {format_bool(args.recursive)}\n"
        f"[bold]Format:[/bold] {cli_config.export_config.label}\n"
        f"[bold]Output dir:[/bold] {cli_config.output_dir}\n"
        f"[bold]Delete remote:[/bold] {format_bool(cli_config.should_delete)}\n"
        f"[bold]Export concurrency:[/bold] {cli_config.export_concurrency}"
    )
    rich_ui.print_panel("Batch Configuration", config_content, style="cyan")

    print_account_pool(cli_config.execution)

    semaphore = asyncio.Semaphore(args.concurrency)
    results: list[dict[str, object]] = []
    account_lock = asyncio.Lock()
    account_index_counter = 0

    async def limited_process(index: int, file_path: Path) -> dict[str, object]:
        nonlocal account_index_counter
        # 使用锁保护账号计数器，确保并发安全
        async with account_lock:
            current_account_index = account_index_counter
            account_index_counter += 1
        
        async with semaphore:
            account = cli_config.execution.accounts[current_account_index % len(cli_config.execution.accounts)]
            return await _process_file(
                file_path=str(file_path),
                index=index,
                total=len(source_files),
                account=account,
                cli_config=cli_config,
            )

    processed_count = 0
    for group_index, group in enumerate(grouped_files, start=1):
        rich_ui.print_header(f"Batch Group {group_index}/{len(grouped_files)}", char="─")
        rich_ui.print_info(f"Files in group: {len(group)}")
        group_results = await asyncio.gather(
            *(limited_process(processed_count + index, file_path) for index, file_path in enumerate(group))
        )
        results.extend(group_results)
        processed_count += len(group)

    succeeded = [result for result in results if result["success"]]
    failed = [result for result in results if not result["success"]]

    summary_content = (
        f"[bold green]Succeeded:[/bold green] {len(succeeded)}\n"
        f"[bold red]Failed:[/bold red] {len(failed)}"
    )
    rich_ui.print_panel("Batch Summary", summary_content, style="green" if not failed else "yellow")

    if failed:
        rich_ui.print_error("\nFailed files:")
        for item in failed:
            rich_ui.console.print(f"  [red]•[/red] {Path(str(item['file_path'])).name}: [dim]{item['error']}[/dim]")
        return 1
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
