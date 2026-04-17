from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from media_tools.transcribe.accounts import ExecutionAccount, mark_account_success
from media_tools.transcribe.cli.common import FlowCliConfig, ensure_auth_state_exists
from media_tools.transcribe.flow import FlowResult
from media_tools.transcribe.result_metadata import write_result_metadata


@dataclass(frozen=True, slots=True)
class FlowExecutionOutcome:
    source_path: Path
    account: ExecutionAccount
    flow_result: FlowResult
    metadata_path: Path


async def execute_flow_once(
    *,
    source_path: Path,
    account: ExecutionAccount,
    cli_config: FlowCliConfig,
) -> FlowExecutionOutcome:
    ensure_auth_state_exists(account)
    from media_tools.transcribe.flow import run_real_flow

    flow_result = await run_real_flow(
        file_path=source_path,
        auth_state_path=account.auth_state_path,
        download_dir=cli_config.output_dir,
        export_config=cli_config.export_config,
        should_delete=cli_config.should_delete,
        account_id=account.account_id,
        export_gate=cli_config.export_gate,
    )
    metadata_path = write_result_metadata(
        flow_result.export_path,
        {
            "recordId": flow_result.record_id,
            "genRecordId": flow_result.gen_record_id,
            "accountId": account.account_id,
        },
    )
    mark_account_success(account.account_id)
    return FlowExecutionOutcome(
        source_path=source_path,
        account=account,
        flow_result=flow_result,
        metadata_path=metadata_path,
    )


async def execute_flow_with_fallback(
    *,
    source_path: Path,
    cli_config: FlowCliConfig,
    announce_accounts: bool = False,
) -> FlowExecutionOutcome:
    last_error: Exception | None = None
    for index, account in enumerate(cli_config.execution.accounts):
        try:
            return await execute_flow_once(source_path=source_path, account=account, cli_config=cli_config)
        except Exception as error:
            last_error = error
            if announce_accounts:
                print(f"Account {account.account_id} failed: {error}")
                if index < len(cli_config.execution.accounts) - 1:
                    print("Trying next account...")
    raise last_error or RuntimeError("No accounts available")
