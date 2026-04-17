from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any

import questionary

from media_tools.transcribe.cli.main import DIRECT_COMMANDS, GROUP_COMMANDS, run as run_cli


@dataclass(frozen=True, slots=True)
class MenuItem:
    title: str
    description: str
    action: str
    icon: str


def build_main_menu() -> list[MenuItem]:
    items: list[MenuItem] = []
    for name, (title, desc) in DIRECT_COMMANDS.items():
        items.append(MenuItem(title=title, description=desc, action=f"direct:{name}", icon=">"))
    for name, (title, _) in GROUP_COMMANDS.items():
        items.append(MenuItem(title=title, description=f"{title} commands", action=f"group:{name}", icon="+"))
    items.append(MenuItem(title="exit", description="Exit", action="exit", icon="x"))
    return items


def build_group_menu(group_name: str) -> list[MenuItem]:
    title, subcommands = GROUP_COMMANDS[group_name]
    items: list[MenuItem] = []
    for sub_name, desc in subcommands.items():
        items.append(
            MenuItem(title=sub_name, description=desc, action=f"sub:{group_name}:{sub_name}", icon=">")
        )
    items.append(MenuItem(title="back", description="Back", action="back", icon="<"))
    return items


def execute_direct_command(command_name: str, argv: list[str]) -> int:
    if command_name not in DIRECT_COMMANDS:
        print(f"unknown command '{command_name}'", file=sys.stderr)
        return 2
    return run_cli([command_name, *argv])


def execute_sub_command(group_name: str, sub_name: str, argv: list[str]) -> int:
    group = GROUP_COMMANDS.get(group_name)
    if not group:
        print(f"unknown group '{group_name}'", file=sys.stderr)
        return 2
    _, subs = group
    if sub_name not in subs:
        print(f"unknown subcommand '{sub_name}'", file=sys.stderr)
        return 2
    return run_cli([group_name, sub_name, *argv])


async def run(argv: list[str]) -> int:
    del argv
    choice = questionary.select(
        "qwen-transcribe",
        choices=[
            questionary.Choice(
                title=f"{item.icon} {item.title}",
                value=item.action,
                description=item.description,
            )
            for item in build_main_menu()
        ],
    ).ask()
    if choice == "exit":
        return 0
    return 0
