from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from qwen_transcribe.accounts import ExecutionAccount
from qwen_transcribe.cli.common import (
    chunk_paths,
    collect_batch_sources,
    ensure_auth_state_exists,
    validate_source_file,
)
from qwen_transcribe.errors import AuthenticationRequiredError, InputValidationError


class CliCommonTests(unittest.TestCase):
    def test_validate_source_file_accepts_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "clip.mp4"
            target.write_bytes(b"ok")

            resolved = validate_source_file(target)

            self.assertTrue(resolved.samefile(target))

    def test_validate_source_file_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing.mp4"

            with self.assertRaises(InputValidationError):
                validate_source_file(missing)

    def test_ensure_auth_state_exists_gives_actionable_message(self) -> None:
        account = ExecutionAccount(
            account_id="account-a",
            account_label="主账号",
            auth_state_path=Path("/tmp/not-real-account-a.json"),
            accounts_file_path=Path("/tmp/accounts.json"),
        )

        with self.assertRaises(AuthenticationRequiredError) as context:
            ensure_auth_state_exists(account)

        self.assertIn("qwen-transcribe auth --account account-a", str(context.exception))

    def test_collect_batch_sources_scans_directory_with_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "a.mp4").write_text("a", encoding="utf-8")
            (root / "b.txt").write_text("b", encoding="utf-8")

            files = collect_batch_sources([str(root)])

        self.assertEqual([path.name for path in files], ["a.mp4"])

    def test_collect_batch_sources_supports_recursive_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            nested = root / "nested"
            nested.mkdir()
            (nested / "a.mp4").write_text("a", encoding="utf-8")

            files = collect_batch_sources([str(root)], recursive=True)

        self.assertEqual([path.name for path in files], ["a.mp4"])

    def test_chunk_paths_splits_groups(self) -> None:
        paths = [Path(f"/tmp/{index}.mp4") for index in range(5)]
        grouped = chunk_paths(paths, 2)

        self.assertEqual([len(group) for group in grouped], [2, 2, 1])
