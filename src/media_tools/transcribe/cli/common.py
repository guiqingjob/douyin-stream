from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from media_tools.transcribe.accounts import ExecutionAccount, ExecutionAccounts
from media_tools.transcribe.errors import AuthenticationRequiredError, InputValidationError
from media_tools.transcribe.runtime import ExportConfig, as_absolute


@dataclass(frozen=True, slots=True)
class FlowCliConfig:
    output_dir: Path
    export_config: ExportConfig
    export_concurrency: int
    export_gate: asyncio.Semaphore
    should_delete: bool
    execution: ExecutionAccounts


def validate_source_file(path: str | Path) -> Path:
    resolved = as_absolute(path)
    if not resolved.exists() or not resolved.is_file():
        raise InputValidationError(f"Source file does not exist: {resolved}")
    return resolved


def ensure_auth_state_exists(account: ExecutionAccount) -> None:
    if account.auth_state_path.exists():
        return
    account_flag = f" --account {account.account_id}" if account.account_id else ""
    raise AuthenticationRequiredError(
        f"Missing auth state: {account.auth_state_path}. Run: qwen-transcribe auth{account_flag}"
    )


def collect_batch_sources(
    sources: list[str],
    *,
    pattern: str = "*.mp4",
    recursive: bool = False,
) -> list[Path]:
    paths: list[Path] = []
    for item in sources:
        path = as_absolute(item)
        if path.is_dir():
            iterator = path.rglob(pattern) if recursive else path.glob(pattern)
            paths.extend([p for p in iterator if p.is_file()])
        else:
            paths.append(validate_source_file(path))
    return sorted({p.resolve() for p in paths})


def chunk_paths(paths: list[Path], group_size: int) -> list[list[Path]]:
    size = max(1, int(group_size))
    return [paths[index : index + size] for index in range(0, len(paths), size)]
