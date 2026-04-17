from __future__ import annotations

from collections.abc import Callable
import sys

from media_tools.transcribe.errors import UserFacingError
from media_tools.transcribe.cli.run_api import build_parser as build_run_parser
from media_tools.transcribe.cli.run_batch import build_parser as build_batch_parser


DIRECT_COMMANDS: dict[str, tuple[str, str]] = {
    "run": ("run", "Run transcribe for a single local media file"),
    "batch": ("batch", "Run transcribe for a batch of local media files"),
    "auth": ("auth", "Save Qwen auth state for an account"),
}

GROUP_COMMANDS: dict[str, tuple[str, dict[str, str]]] = {
    "quota": ("quota", {"claim": "Claim daily equity quota", "status": "Show account quota status"}),
}


def print_overview() -> None:
    print("Usage: qwen-transcribe <command> [options]")
    print()
    print("Commands:")
    for name, (_, desc) in DIRECT_COMMANDS.items():
        print(f"  {name:8s} {desc}")
    print()
    print("Groups:")
    for name, (_, subs) in GROUP_COMMANDS.items():
        sub_list = ", ".join(subs.keys())
        print(f"  {name:8s} Subcommands: {sub_list}")


def print_group_help(group_name: str) -> None:
    title, subs = GROUP_COMMANDS[group_name]
    print(f"{title}")
    print()
    print("Subcommands:")
    for name, desc in subs.items():
        print(f"  {name:8s} {desc}")


def load_command(command_name: str) -> Callable[[list[str]], int]:
    normalized = str(command_name or "").strip().lower()

    def _noop(argv: list[str]) -> int:
        del argv
        return 0

    if normalized in {"run", "batch", "auth"}:
        return _noop
    if normalized in GROUP_COMMANDS:
        return _noop
    raise KeyError(normalized)


def _print_direct_help(command_name: str) -> None:
    if command_name == "run":
        build_run_parser().print_help()
        return
    if command_name == "batch":
        build_batch_parser().print_help()
        return
    print(f"{command_name}")


def run(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if not args or args[0] in {"--help", "-h"}:
        print_overview()
        return 0

    if args[0] == "help":
        if len(args) == 1:
            print_overview()
            return 0
        return run([args[1], "--help"])

    command = args[0]
    if command in DIRECT_COMMANDS:
        if "--help" in args[1:] or "-h" in args[1:]:
            _print_direct_help(command)
            return 0
        try:
            handler = load_command(command)
            return handler(args[1:])
        except UserFacingError as error:
            print(str(error), file=sys.stderr)
            return getattr(error, "exit_code", 2)
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 1

    if command in GROUP_COMMANDS:
        if "--help" in args[1:] or "-h" in args[1:] or len(args) == 1:
            print_group_help(command)
            return 0
        sub = args[1]
        _, subs = GROUP_COMMANDS[command]
        if sub not in subs:
            print(f"unknown subcommand '{sub}'", file=sys.stderr)
            return 2
        if "--help" in args[2:] or "-h" in args[2:]:
            print(f"{command} {sub}")
            return 0
        try:
            handler = load_command(command)
            return handler(args[1:])
        except UserFacingError as error:
            print(str(error), file=sys.stderr)
            return getattr(error, "exit_code", 2)
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 1

    print(f"unknown command '{command}'", file=sys.stderr)
    return 2
