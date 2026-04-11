from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from typing import Any

from rich.console import Console
from rich.table import Table
from rich import box

from ..errors import QwenTranscribeError

console = Console()

CommandSpec = tuple[str, str, str]
HELP_TOKENS = {"-h", "--help", "help"}

DIRECT_COMMANDS: dict[str, CommandSpec] = {
    "menu": ("Interactive menu navigation (recommended for beginners)", "media_tools.transcribe.cli.interactive_menu", "run"),
    "init": ("Initialize configuration files (use --interactive for wizard)", "media_tools.transcribe.cli.init_wizard", "run"),
    "auth": ("Open a browser and save login storage state", "media_tools.transcribe.cli.auth", "run"),
    "capture": ("Capture browser network traffic into local JSONL logs", "media_tools.transcribe.cli.capture", "run"),
    "summarize": ("Summarize captured network logs", "media_tools.transcribe.cli.summarize_network", "run"),
    "run": ("Run the Qwen API flow for one local media file", "media_tools.transcribe.cli.run_api", "run"),
    "batch": ("Batch-process multiple local media files", "media_tools.transcribe.cli.run_batch", "run"),
}

GROUP_COMMANDS: dict[str, tuple[str, dict[str, CommandSpec]]] = {
    "accounts": (
        "Account inspection commands",
        {
            "status": ("Show auth/quota status for configured accounts", "media_tools.transcribe.cli.accounts_status", "run"),
        },
    ),
    "quota": (
        "Quota maintenance commands",
        {
            "claim": ("Claim upload quota for one or more accounts", "media_tools.transcribe.cli.claim_equity", "run"),
            "needed": ("Claim upload quota only for accounts that need it", "media_tools.transcribe.cli.claim_needed", "run"),
        },
    ),
    "cleanup": (
        "Cleanup commands",
        {
            "remote-records": (
                "Delete remote records referenced by local metadata sidecars",
                "media_tools.transcribe.cli.cleanup_remote_records",
                "run",
            ),
        },
    ),
}


def print_overview() -> None:
    console.print("\n[bold cyan]Usage:[/bold cyan]")
    console.print("  [green]qwen-transcribe[/green] [bold]<command>[/bold] [args]")
    console.print("  [green]qwen-transcribe[/green] [bold]<group>[/bold] [bold]<subcommand>[/bold] [args]")
    
    # Commands table
    cmd_table = Table(title="Commands", box=box.ROUNDED, style="cyan")
    cmd_table.add_column("Command", style="bold green", width=12)
    cmd_table.add_column("Description")
    
    for name, (description, _, _) in DIRECT_COMMANDS.items():
        cmd_table.add_row(name, description)
    
    console.print()
    console.print(cmd_table)
    
    # Groups table
    grp_table = Table(title="Groups", box=box.ROUNDED, style="cyan")
    grp_table.add_column("Group", style="bold magenta", width=12)
    grp_table.add_column("Description")
    grp_table.add_column("Subcommands", style="dim")
    
    for group_name, (group_description, subcommands) in GROUP_COMMANDS.items():
        subs = ", ".join(subcommands.keys())
        grp_table.add_row(group_name, group_description, subs)
    
    console.print()
    console.print(grp_table)
    
    console.print("\n[dim]Run `qwen-transcribe <command> --help` for command-specific options.[/dim]\n")


def print_group_overview(group_name: str) -> None:
    group_description, subcommands = GROUP_COMMANDS[group_name]
    console.print(f"\n[bold cyan]{group_name}[/bold cyan] - {group_description}")
    
    sub_table = Table(title="Subcommands", box=box.ROUNDED, style="cyan")
    sub_table.add_column("Subcommand", style="bold green", width=16)
    sub_table.add_column("Description")
    
    for subcommand_name, (description, _, _) in subcommands.items():
        sub_table.add_row(subcommand_name, description)
    
    console.print()
    console.print(sub_table)
    console.print(f"\n[dim]Run `qwen-transcribe {group_name} <subcommand> --help` for subcommand-specific options.[/dim]\n")


def load_command(module_name: str, attribute: str) -> Any:
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def is_help_token(value: str) -> bool:
    return value in HELP_TOKENS


def normalize_forwarded_args(argv: list[str]) -> list[str]:
    if argv and argv[0] == "help":
        return ["--help", *argv[1:]]
    # 避免重复添加 --help
    if argv and argv[0] in HELP_TOKENS:
        return argv
    return argv


def execute_command(spec: CommandSpec, argv: list[str]) -> int:
    _, module_name, attribute = spec
    target = load_command(module_name, attribute)
    # 检查是否已经是 help 调用，避免重复
    is_help_call = "--help" in argv or "-h" in argv
    args_to_use = normalize_forwarded_args(argv) if not is_help_call else argv
    try:
        result = target(args_to_use)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
    except QwenTranscribeError as error:
        print_error(str(error))
        return int(error.exit_code)
    except SystemExit as error:
        code = error.code
        if code is None:
            return 0
        try:
            return int(code)
        except (TypeError, ValueError):
            return 1
    
    # 处理命令函数返回None的情况
    if result is None:
        return 0
    return int(result)


def print_error(message: str) -> None:
    print(f"qwen-transcribe: error: {message}", file=sys.stderr)


def dispatch_help(argv: list[str]) -> int:
    if not argv:
        print_overview()
        return 0

    command = argv[0]
    rest = argv[1:]
    if command in DIRECT_COMMANDS:
        return execute_command(DIRECT_COMMANDS[command], ["--help", *rest])
    if command in GROUP_COMMANDS:
        if not rest:
            print_group_overview(command)
            return 0
        subcommands = GROUP_COMMANDS[command][1]
        subcommand = rest[0]
        if subcommand not in subcommands:
            print_error(f"unknown subcommand '{command} {subcommand}'")
            return 2
        return execute_command(subcommands[subcommand], ["--help", *rest[1:]])

    print_error(f"unknown command '{command}'")
    return 2


def run(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print_overview()
        return 0

    command = args[0]
    rest = args[1:]

    if is_help_token(command):
        return dispatch_help(rest)

    if command in DIRECT_COMMANDS:
        return execute_command(DIRECT_COMMANDS[command], rest)

    if command in GROUP_COMMANDS:
        if not rest or is_help_token(rest[0]):
            print_group_overview(command)
            return 0
        subcommands = GROUP_COMMANDS[command][1]
        subcommand = rest[0]
        if subcommand not in subcommands:
            print_error(f"unknown subcommand '{command} {subcommand}'")
            return 2
        return execute_command(subcommands[subcommand], rest[1:])

    print_error(f"unknown command '{command}'")
    return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
