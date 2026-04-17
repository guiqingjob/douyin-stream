from __future__ import annotations

import subprocess
import sys


def _wait_for_key() -> None:
    try:
        input("按回车继续...")
    except (KeyboardInterrupt, EOFError):
        return


def _run_transcribe_cli(args: list[str]) -> int:
    result = subprocess.run([sys.executable, "-m", "media_tools.transcribe.cli.main", *args])
    return int(getattr(result, "returncode", 0) or 0)


def cmd_transcribe_run() -> None:
    _run_transcribe_cli(["run"])
    _wait_for_key()


def cmd_transcribe_batch() -> None:
    _run_transcribe_cli(["batch"])
    _wait_for_key()


def cmd_transcribe_auth() -> None:
    _run_transcribe_cli(["init"])
    _wait_for_key()


def cmd_transcribe_accounts() -> None:
    _run_transcribe_cli(["status"])
    _wait_for_key()
