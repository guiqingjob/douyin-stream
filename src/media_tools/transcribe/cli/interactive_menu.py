"""交互式菜单导航CLI"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from typing import Any, Callable

import questionary
from rich.console import Console

from ..errors import QwenTranscribeError
from .main import (
    DIRECT_COMMANDS,
    GROUP_COMMANDS,
    print_error,
    normalize_forwarded_args,
)

console = Console()


# 菜单项定义
class MenuItem:
    def __init__(self, title: str, description: str, action: str | Callable, icon: str = "•"):
        self.title = title
        self.description = description
        self.action = action
        self.icon = icon


def build_main_menu() -> list[MenuItem]:
    """构建主菜单"""
    items = []
    
    # 直接命令
    for name, (description, module, func) in DIRECT_COMMANDS.items():
        items.append(MenuItem(
            title=name,
            description=description,
            action=f"direct:{name}",
            icon="▶"
        ))
    
    # 命令组
    for group_name, (group_desc, subcommands) in GROUP_COMMANDS.items():
        items.append(MenuItem(
            title=group_name,
            description=f"{group_desc} ({', '.join(subcommands.keys())})",
            action=f"group:{group_name}",
            icon="📁"
        ))
    
    items.append(MenuItem(
        title="exit",
        description="退出程序",
        action="exit",
        icon="❌"
    ))
    
    return items


def build_group_menu(group_name: str) -> list[MenuItem]:
    """构建子菜单"""
    _, subcommands = GROUP_COMMANDS[group_name]
    items = []
    
    for sub_name, (sub_desc, module, func) in subcommands.items():
        items.append(MenuItem(
            title=sub_name,
            description=sub_desc,
            action=f"sub:{group_name}:{sub_name}",
            icon="▶"
        ))
    
    items.append(MenuItem(
        title="返回",
        description="返回上一级菜单",
        action="back",
        icon="◀"
    ))
    
    return items


def show_header(text: str = "Qwen Transcribe") -> None:
    """显示菜单头部"""
    console.print(f"\n[bold cyan]{'═' * 50}[/bold cyan]")
    console.print(f"[bold cyan]{text.center(50)}[/bold cyan]")
    console.print(f"[bold cyan]{'═' * 50}[/bold cyan]")


def show_menu_prompt(items: list[MenuItem], current_menu: str) -> str:
    """显示交互式菜单选择"""
    choices = []
    for item in items:
        display_text = f"{item.icon} {item.title:<15} - {item.description}"
        choices.append(questionary.Choice(title=display_text, value=item.action))
    
    # 根据当前菜单设置提示文本
    if current_menu == "main":
        message = "[bold]请选择命令:[/bold] (使用 ↑↓ 键导航，Enter 确认)"
    else:
        message = f"[bold]{current_menu} 子命令:[/bold] (使用 ↑↓ 键导航，Enter 确认)"
    
    answer = questionary.select(
        message,
        choices=choices,
        use_shortcuts=True,
        qmark="📋"
    ).ask()
    
    return answer


def execute_direct_command(name: str, argv: list[str]) -> int:
    """执行直接命令"""
    if name not in DIRECT_COMMANDS:
        print_error(f"unknown command '{name}'")
        return 2
    
    spec = DIRECT_COMMANDS[name]
    _, module_name, attribute = spec
    
    # 动态加载
    import importlib
    module = importlib.import_module(module_name)
    target = getattr(module, attribute)
    
    try:
        result = target(normalize_forwarded_args(argv))
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        return int(result)
    except QwenTranscribeError as error:
        print_error(str(error))
        return int(error.exit_code)
    except Exception as error:
        print_error(str(error))
        return 1


def execute_sub_command(group_name: str, sub_name: str, argv: list[str]) -> int:
    """执行子命令"""
    if group_name not in GROUP_COMMANDS:
        print_error(f"unknown group '{group_name}'")
        return 2
    
    _, subcommands = GROUP_COMMANDS[group_name]
    if sub_name not in subcommands:
        print_error(f"unknown subcommand '{sub_name}'")
        return 2
    
    spec = subcommands[sub_name]
    _, module_name, attribute = spec
    
    # 动态加载
    import importlib
    module = importlib.import_module(module_name)
    target = getattr(module, attribute)
    
    try:
        result = target(normalize_forwarded_args(argv))
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        return int(result)
    except QwenTranscribeError as error:
        print_error(str(error))
        return int(error.exit_code)
    except Exception as error:
        print_error(str(error))
        return 1


async def run(argv: list[str] | None = None) -> int:
    """运行交互式菜单"""
    parser = argparse.ArgumentParser(
        prog="qwen-transcribe menu",
        description="Interactive menu navigation for Qwen Transcribe.",
    )
    args = parser.parse_args(argv)
    
    console.print("\n[bold green]🚀 欢迎使用 Qwen Transcribe 交互菜单！[/bold green]")
    console.print("[dim]使用 ↑↓ 方向键选择命令，按 Enter 执行，按 ESC 退出[/dim]\n")
    
    current_menu = "main"
    menu_stack = []
    
    while True:
        try:
            if current_menu == "main":
                items = build_main_menu()
                show_header("Qwen Transcribe - 主菜单")
                answer = show_menu_prompt(items, current_menu)
                
                if answer is None or answer == "exit":  # ESC 或选择 exit
                    console.print("\n[bold yellow]👋 再见！[/bold yellow]\n")
                    return 0
                
                if answer.startswith("direct:"):
                    cmd_name = answer.split(":", 1)[1]
                    console.print(f"\n[bold cyan]▶ 执行命令: {cmd_name}[/bold cyan]\n")
                    exit_code = execute_direct_command(cmd_name, [])
                    if exit_code != 0:
                        console.print(f"\n[bold red]❌ 命令执行失败 (退出码: {exit_code})[/bold red]")
                    else:
                        console.print(f"\n[bold green]✅ 命令执行成功[/bold green]")
                    
                    # 等待用户确认后返回菜单
                    questionary.confirm("按回车返回菜单", qmark="⏎").ask()
                
                elif answer.startswith("group:"):
                    group_name = answer.split(":", 1)[1]
                    menu_stack.append(current_menu)
                    current_menu = group_name
            
            elif current_menu in GROUP_COMMANDS:
                items = build_group_menu(current_menu)
                show_header(f"{current_menu} - 子菜单")
                answer = show_menu_prompt(items, current_menu)
                
                if answer is None or answer == "back":  # ESC 或返回
                    current_menu = menu_stack.pop() if menu_stack else "main"
                    continue
                
                if answer.startswith("sub:"):
                    parts = answer.split(":")
                    group_name = parts[1]
                    sub_name = parts[2]
                    console.print(f"\n[bold cyan]▶ 执行命令: {group_name} {sub_name}[/bold cyan]\n")
                    exit_code = execute_sub_command(group_name, sub_name, [])
                    if exit_code != 0:
                        console.print(f"\n[bold red]❌ 命令执行失败 (退出码: {exit_code})[/bold red]")
                    else:
                        console.print(f"\n[bold green]✅ 命令执行成功[/bold green]")
                    
                    # 等待用户确认后返回菜单
                    questionary.confirm("按回车返回菜单", qmark="⏎").ask()
        
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]👋 已取消操作[/bold yellow]\n")
            return 0
        except Exception as error:
            console.print(f"\n[bold red]❌ 发生错误: {error}[/bold red]")
            return 1
    
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
