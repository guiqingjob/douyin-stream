from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..accounts import ExecutionAccount, mark_account_success
from ..flow import FlowResult
from ..result_metadata import write_result_metadata
from .common import FlowCliConfig, ensure_auth_state_exists, print_selected_account


@dataclass(frozen=True, slots=True)
class FlowExecutionOutcome:
    source_path: Path
    account: ExecutionAccount
    flow_result: FlowResult
    metadata_path: Path


def result_metadata_payload(result: FlowResult) -> dict[str, str | bool]:
    return {
        "record_id": result.record_id,
        "gen_record_id": result.gen_record_id,
        "remote_deleted": result.remote_deleted,
        "remote_delete_status": "success" if result.remote_deleted else "failed",
    }


def write_execution_metadata(result: FlowResult) -> Path:
    return write_result_metadata(result.export_path, result_metadata_payload(result))


async def execute_flow_once(
    *,
    source_path: Path,
    account: ExecutionAccount,
    cli_config: FlowCliConfig,
) -> FlowExecutionOutcome:
    from ..flow import run_real_flow

    ensure_auth_state_exists(account)
    result = await run_real_flow(
        file_path=source_path,
        auth_state_path=account.auth_state_path,
        download_dir=cli_config.output_dir,
        export_config=cli_config.export_config,
        should_delete=cli_config.should_delete,
        account_id=account.account_id,
        export_gate=cli_config.export_gate,
    )
    metadata_path = write_execution_metadata(result)
    mark_account_success(account.account_id)
    return FlowExecutionOutcome(
        source_path=source_path,
        account=account,
        flow_result=result,
        metadata_path=metadata_path,
    )


async def execute_flow_with_fallback(
    *,
    source_path: Path,
    cli_config: FlowCliConfig,
    announce_accounts: bool = False,
) -> FlowExecutionOutcome:
    last_error: Exception | None = None
    for account in cli_config.execution.accounts:
        try:
            if announce_accounts:
                print_selected_account(account)
            return await execute_flow_once(source_path=source_path, account=account, cli_config=cli_config)
        except Exception as error:
            last_error = error
            if len(cli_config.execution.accounts) == 1:
                raise
            print(f"Account {account.account_id or 'default'} failed: {error}")
            print("Trying next account...")
    assert last_error is not None
    raise last_error
