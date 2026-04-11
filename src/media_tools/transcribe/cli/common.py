from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path

from ..accounts import ExecutionAccount, ExecutionAccounts, normalize_account_strategy, resolve_execution_accounts
from ..config import load_config
from ..errors import AuthenticationRequiredError, InputValidationError
from ..runtime import ExportConfig, as_absolute, get_export_config


@dataclass(frozen=True, slots=True)
class FlowCliConfig:
    output_dir: Path
    export_config: ExportConfig
    export_concurrency: int
    export_gate: asyncio.Semaphore
    should_delete: bool
    execution: ExecutionAccounts


def command_parser(command_name: str, description: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog=f"qwen-transcribe {command_name}", description=description)


def add_flow_execution_arguments(parser: argparse.ArgumentParser) -> None:
    app_config = load_config()
    parser.add_argument(
        "--format",
        default=app_config.export_format,
        choices=["md", "markdown", "docx"],
        help="Export format (default: %(default)s)",
    )
    parser.add_argument(
        "--delete",
        dest="delete",
        action="store_true",
        default=None,
        help="Delete the remote record after export",
    )
    parser.add_argument(
        "--keep-remote",
        dest="delete",
        action="store_false",
        help="Keep the remote record after export",
    )
    parser.add_argument("--account", default=app_config.default_account, help="Use a specific account id")
    parser.add_argument(
        "--account-strategy",
        default=app_config.default_account_strategy,
        choices=["round-robin", "failover", "sticky"],
        help="Account selection strategy when multiple accounts are configured",
    )
    parser.add_argument(
        "--output-dir",
        "--download-dir",
        dest="output_dir",
        default=str(app_config.paths.download_dir),
        help="Directory where exported files and metadata sidecars are written (default: %(default)s)",
    )
    parser.add_argument(
        "--export-concurrency",
        type=int,
        default=app_config.export_concurrency,
        help="How many export requests may run at once (default: %(default)s)",
    )


def resolve_flow_cli_config(args: argparse.Namespace) -> FlowCliConfig:
    app_config = load_config()
    should_delete = args.delete
    if should_delete is None:
        should_delete = app_config.delete_after_export

    export_concurrency = int(args.export_concurrency)
    if export_concurrency <= 0:
        raise InputValidationError("--export-concurrency must be a positive integer")

    execution = resolve_execution_accounts(
        account_id=args.account,
        strategy=normalize_account_strategy(args.account_strategy),
    )
    return FlowCliConfig(
        output_dir=as_absolute(args.output_dir),
        export_config=get_export_config(args.format),
        export_concurrency=export_concurrency,
        export_gate=asyncio.Semaphore(max(1, export_concurrency)),
        should_delete=should_delete,
        execution=execution,
    )


def format_bool(value: bool) -> str:
    return "yes" if value else "no"


def validate_source_file(raw_path: str | Path) -> Path:
    path = as_absolute(raw_path)
    if not path.exists():
        raise InputValidationError(f"input file does not exist: {path}")
    if not path.is_file():
        raise InputValidationError(f"input path is not a file: {path}")
    return path


def validate_source_files(raw_paths: list[str]) -> list[Path]:
    return [validate_source_file(path) for path in raw_paths]


def collect_batch_sources(
    raw_inputs: list[str],
    *,
    pattern: str = "*.mp4",
    recursive: bool = False,
) -> list[Path]:
    collected: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        collected.append(resolved)

    for raw in raw_inputs:
        candidate = as_absolute(raw)
        if not candidate.exists():
            raise InputValidationError(f"input path does not exist: {candidate}")
        if candidate.is_file():
            add(candidate)
            continue
        if not candidate.is_dir():
            raise InputValidationError(f"input path is neither file nor directory: {candidate}")

        matcher = candidate.rglob if recursive else candidate.glob
        matches = sorted(path for path in matcher(pattern) if path.is_file())
        if not matches:
            raise InputValidationError(f"directory has no files matching {pattern!r}: {candidate}")
        for match in matches:
            add(match)

    if not collected:
        raise InputValidationError("no input files found")
    return collected


def chunk_paths(paths: list[Path], group_size: int) -> list[list[Path]]:
    if group_size <= 0:
        raise InputValidationError("--group-size must be a positive integer")
    return [paths[index : index + group_size] for index in range(0, len(paths), group_size)]


def ensure_auth_state_exists(account: ExecutionAccount) -> None:
    if account.auth_state_path.exists():
        return
    if account.account_id:
        raise AuthenticationRequiredError(
            f"missing login state for account '{account.account_id}': {account.auth_state_path}. "
            f"Run `qwen-transcribe auth --account {account.account_id}` first."
        )
    raise AuthenticationRequiredError(
        f"missing login state: {account.auth_state_path}. Run `qwen-transcribe auth` first."
    )


def print_account_pool(execution: ExecutionAccounts) -> None:
    if len(execution.accounts) <= 1:
        return
    print(f"Account strategy: {execution.strategy}")
    print(f"Candidate accounts: {', '.join(item.account_id for item in execution.accounts)}")


def print_selected_account(account: ExecutionAccount) -> None:
    if account.account_id:
        print(f"Using account: {account.account_label} ({account.account_id})")
    else:
        print("Using default single-account auth state")
