from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

# 全局控制台实例
console = Console()


def print_panel(title: str, content: str, style: str = "blue") -> None:
    """打印带边框的面板"""
    console.print(Panel(content, title=title, style=style, border_style=style))


def print_success(message: str) -> None:
    """打印成功消息"""
    console.print(f"[bold green]✅ {message}[/bold green]")


def print_error(message: str) -> None:
    """打印错误消息"""
    console.print(f"[bold red]❌ {message}[/bold red]")


def print_warning(message: str) -> None:
    """打印警告消息"""
    console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")


def print_info(message: str) -> None:
    """打印信息消息"""
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")


def print_step(step_num: int, title: str, content: str = "") -> None:
    """打印步骤信息"""
    console.print(f"\n[bold cyan]📝 步骤 {step_num}[/bold cyan]: [bold]{title}[/bold]")
    if content:
        console.print(f"   {content}")


def create_progress() -> Progress:
    """创建标准进度条"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    )


def create_table(title: str, columns: list[str], rows: list[list[str]]) -> Table:
    """创建表格"""
    table = Table(title=title, box=box.ROUNDED, style="cyan")
    for col in columns:
        table.add_column(col, style="bold")
    for row in rows:
        table.add_row(*row)
    return table


def ask_prompt(question: str, default: str = "", required: bool = False) -> str:
    """交互式提示"""
    while True:
        if default:
            answer = Prompt.ask(question, default=default, console=console)
        else:
            answer = Prompt.ask(question, console=console)
        
        if not answer and required:
            console.print("[bold red]  此项为必填项，请输入有效值。[/bold red]")
            continue
        if not answer and not required:
            return default
        return answer


def ask_confirm(question: str, default: bool = True) -> bool:
    """确认提示"""
    return Confirm.ask(question, default=default, console=console)


def print_key_value(key: str, value: str, indent: int = 0) -> None:
    """打印键值对"""
    prefix = "  " * indent
    console.print(f"{prefix}[bold]{key}:[/bold] {value}")


def print_header(text: str, char: str = "=") -> None:
    """打印标题头"""
    width = 60
    line = char * width
    console.print(f"\n{line}", style="bold cyan")
    console.print(f"{text}", style="bold cyan")
    console.print(f"{line}", style="bold cyan")


def print_divider() -> None:
    """打印分割线"""
    console.print("\n[dim]" + "─" * 60 + "[/dim]\n")
