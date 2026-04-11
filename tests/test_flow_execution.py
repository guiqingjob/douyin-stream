from __future__ import annotations

from pathlib import Path
import asyncio
import tempfile
from unittest.mock import AsyncMock, patch
import unittest

from qwen_transcribe.accounts import ExecutionAccount, ExecutionAccounts
from qwen_transcribe.cli.common import FlowCliConfig
from qwen_transcribe.cli.flow_execution import FlowExecutionOutcome, execute_flow_once, execute_flow_with_fallback
from qwen_transcribe.flow import FlowResult
from qwen_transcribe.runtime import ExportConfig


def build_cli_config(accounts: list[ExecutionAccount]) -> FlowCliConfig:
    return FlowCliConfig(
        output_dir=Path("/tmp/exports"),
        export_config=ExportConfig(file_type=3, extension=".md", label="md"),
        export_concurrency=2,
        export_gate=asyncio.Semaphore(2),
        should_delete=True,
        execution=ExecutionAccounts(
            strategy="round-robin",
            pool_state_path=Path("/tmp/account-pool-state.json"),
            accounts=accounts,
        ),
    )


class FlowExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_flow_once_writes_metadata_and_marks_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            auth_state = Path(tmp_dir) / "account-a.json"
            auth_state.write_text("{}", encoding="utf-8")
            account = ExecutionAccount(
                account_id="account-a",
                account_label="主账号",
                auth_state_path=auth_state,
                accounts_file_path=Path(tmp_dir) / "accounts.json",
            )
            cli_config = build_cli_config([account])
            flow_result = FlowResult(
                record_id="record-1",
                gen_record_id="gen-1",
                export_path=Path(tmp_dir) / "result.md",
                remote_deleted=True,
            )

            with patch("qwen_transcribe.flow.run_real_flow", new=AsyncMock(return_value=flow_result)) as mocked_flow:
                with patch(
                    "qwen_transcribe.cli.flow_execution.write_result_metadata",
                    return_value=Path(tmp_dir) / "result.md.meta.json",
                ) as mocked_metadata:
                    with patch("qwen_transcribe.cli.flow_execution.mark_account_success") as mocked_mark:
                        outcome = await execute_flow_once(
                            source_path=Path(tmp_dir) / "input.mp4",
                            account=account,
                            cli_config=cli_config,
                        )

            self.assertEqual(outcome.flow_result, flow_result)
            mocked_flow.assert_awaited_once()
            mocked_metadata.assert_called_once()
            mocked_mark.assert_called_once_with("account-a")

    async def test_execute_flow_with_fallback_tries_next_account_after_failure(self) -> None:
        account_a = ExecutionAccount(
            account_id="account-a",
            account_label="主账号",
            auth_state_path=Path("/tmp/account-a.json"),
            accounts_file_path=Path("/tmp/accounts.json"),
        )
        account_b = ExecutionAccount(
            account_id="account-b",
            account_label="备用账号",
            auth_state_path=Path("/tmp/account-b.json"),
            accounts_file_path=Path("/tmp/accounts.json"),
        )
        cli_config = build_cli_config([account_a, account_b])
        expected = FlowExecutionOutcome(
            source_path=Path("/tmp/input.mp4"),
            account=account_b,
            flow_result=FlowResult(
                record_id="record-2",
                gen_record_id="gen-2",
                export_path=Path("/tmp/result.md"),
                remote_deleted=False,
            ),
            metadata_path=Path("/tmp/result.md.meta.json"),
        )

        with patch(
            "qwen_transcribe.cli.flow_execution.execute_flow_once",
            new=AsyncMock(side_effect=[RuntimeError("boom"), expected]),
        ) as mocked_execute:
            with patch("builtins.print") as mocked_print:
                outcome = await execute_flow_with_fallback(
                    source_path=Path("/tmp/input.mp4"),
                    cli_config=cli_config,
                    announce_accounts=True,
                )

        self.assertEqual(outcome, expected)
        self.assertEqual(mocked_execute.await_count, 2)
        mocked_print.assert_any_call("Account account-a failed: boom")
        mocked_print.assert_any_call("Trying next account...")
