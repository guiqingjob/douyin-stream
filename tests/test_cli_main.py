from __future__ import annotations

from contextlib import redirect_stdout
import io
from unittest.mock import patch
import unittest

from qwen_transcribe.errors import InputValidationError
from qwen_transcribe.cli.main import run


class CliMainTests(unittest.TestCase):
    def test_help_lists_primary_commands(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = run(["--help"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage:", output)
        self.assertIn("auth", output)
        self.assertIn("Commands", output)
        self.assertIn("Groups", output)

    def test_help_alias_behaves_like_overview(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = run(["help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Groups", buffer.getvalue())

    def test_direct_command_help_is_forwarded(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = run(["run", "--help"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("usage: qwen-transcribe run", output)
        self.assertIn("Local media file path", output)
        self.assertIn("--output-dir", output)

    def test_group_help_shows_group_specific_overview(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = run(["quota", "--help"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("quota", output)
        self.assertIn("claim", output)
        self.assertIn("Subcommands", output)

    def test_help_prefix_supports_targeted_command_help(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = run(["help", "run"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Local media file path", buffer.getvalue())

    def test_run_uses_process_argv_when_argument_list_is_missing(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with patch("sys.argv", ["qwen-transcribe", "help", "run"]):
                exit_code = run()

        self.assertEqual(exit_code, 0)
        self.assertIn("Local media file path", buffer.getvalue())

    def test_unknown_command_returns_error_code(self) -> None:
        buffer = io.StringIO()
        with patch("sys.stderr", buffer):
            exit_code = run(["wat"])

        self.assertEqual(exit_code, 2)
        self.assertIn("unknown command 'wat'", buffer.getvalue())

    def test_user_facing_errors_are_printed_to_stderr(self) -> None:
        buffer = io.StringIO()

        def broken_command(argv: list[str]) -> int:
            del argv
            raise InputValidationError("bad input")

        with patch("qwen_transcribe.cli.main.load_command", return_value=broken_command):
            with patch("sys.stderr", buffer):
                exit_code = run(["run"])

        self.assertEqual(exit_code, 2)
        self.assertIn("bad input", buffer.getvalue())
