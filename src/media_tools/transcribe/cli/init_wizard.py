from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..runtime import as_absolute, ensure_dir, load_dotenv
from . import rich_ui


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qwen-transcribe init",
        description="Initialize configuration files for Qwen Transcribe.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing configuration files without asking",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Use interactive wizard mode (default: quick generation)",
    )
    return parser


def ask_question(question: str, default: str = "", required: bool = False) -> str:
    """Ask a question and return the user's answer."""
    return rich_ui.ask_prompt(question, default=default, required=required)


def ask_yes_no(question: str, default: str = "yes") -> bool:
    """Ask a yes/no question. Returns True for yes, False for no."""
    return rich_ui.ask_confirm(question, default=default.lower() in {"yes", "y"})


def check_existing_config(force: bool) -> tuple[bool, bool]:
    """Check if config files exist and ask for overwrite if needed."""
    env_path = Path.cwd() / ".env"
    accounts_path = Path.cwd() / "accounts.json"
    
    env_exists = env_path.exists()
    accounts_exists = accounts_path.exists()
    
    if env_exists or accounts_exists:
        if force:
            return env_exists, accounts_exists
        
        files_found = []
        if env_exists:
            files_found.append(".env")
        if accounts_exists:
            files_found.append("accounts.json")
        
        rich_ui.print_warning(f"发现已存在的配置文件: {', '.join(files_found)}")
        overwrite = ask_yes_no("是否覆盖这些文件", default="no")
        if not overwrite:
            rich_ui.print_info("配置已取消。如需保留现有文件，请使用 --force 参数或手动编辑。")
            sys.exit(0)
    
    return env_exists, accounts_exists


def setup_env_config() -> dict[str, str]:
    """Interactive setup for .env file."""
    rich_ui.print_header("📝 步骤 1/2: 配置环境变量 (.env)")
    rich_ui.print_info("以下配置将保存到 .env 文件中，用于自定义程序行为。")
    rich_ui.print_info("直接按回车将使用默认值。")
    rich_ui.print_divider()
    
    config = {}
    
    # Qwen base URL
    config["QWEN_BASE_URL"] = ask_question(
        "千问基础URL",
        default="https://www.qianwen.com"
    )
    
    # Default account
    config["QWEN_ACCOUNT"] = ask_question(
        "默认账号ID（留空表示使用单账号模式）",
        default="",
        required=False
    )
    
    # Account strategy
    rich_ui.print_divider()
    rich_ui.print_info("账号选择策略:")
    rich_ui.console.print("  [bold]1.[/bold] round-robin - 轮流使用多个账号（推荐）")
    rich_ui.console.print("  [bold]2.[/bold] failover    - 主账号失败后切换备用")
    rich_ui.console.print("  [bold]3.[/bold] sticky      - 优先使用上次成功的账号")
    
    strategy_map = {"1": "round-robin", "2": "failover", "3": "sticky"}
    while True:
        strategy_choice = ask_question(
            "请选择策略 (1-3)",
            default="1",
            required=True
        )
        if strategy_choice in strategy_map:
            config["QWEN_ACCOUNT_STRATEGY"] = strategy_map[strategy_choice]
            break
        rich_ui.print_error("请输入 1、2 或 3。")
    
    # Export format
    rich_ui.print_divider()
    rich_ui.print_info("导出格式:")
    rich_ui.console.print("  [bold]1.[/bold] md (Markdown)")
    rich_ui.console.print("  [bold]2.[/bold] docx (Word文档)")
    
    format_map = {"1": "md", "2": "docx"}
    while True:
        format_choice = ask_question(
            "请选择格式 (1-2)",
            default="1",
            required=True
        )
        if format_choice in format_map:
            config["QWEN_EXPORT_FORMAT"] = format_map[format_choice]
            break
        rich_ui.print_error("请输入 1 或 2。")
    
    # Delete after export
    delete_after = ask_yes_no(
        "\n导出后是否删除远程记录",
        default="yes"
    )
    config["QWEN_DELETE_AFTER_EXPORT"] = "true" if delete_after else "false"
    
    # Download directory
    config["QWEN_DOWNLOAD_DIR"] = ask_question(
        "\n下载目录",
        default="downloads"
    )
    
    # Concurrency
    config["QWEN_EXPORT_CONCURRENCY"] = ask_question(
        "\n导出并发数",
        default="2"
    )
    
    return config


def setup_accounts_config() -> list[dict[str, str]]:
    """Interactive setup for accounts.json file."""
    rich_ui.print_header("👥 步骤 2/2: 配置账号 (accounts.json)")
    rich_ui.print_info("账号配置用于多账号轮询或故障转移。")
    rich_ui.print_info("如果只需使用单账号模式，可以跳过此步骤。")
    rich_ui.print_divider()
    
    has_multiple = ask_yes_no("是否配置多个账号", default="no")
    
    if not has_multiple:
        rich_ui.print_info("\n已跳过账号配置。将使用单账号模式。")
        rich_ui.print_info("提示: 运行 `qwen-transcribe auth` 来保存登录状态。")
        return []
    
    accounts = []
    account_num = 1
    
    while True:
        rich_ui.print_divider()
        rich_ui.print_info(f"账号 {account_num}")
        account_id = ask_question(
            f"账号ID（用于标识，如 account-{account_num}）",
            default=f"account-{account_num}",
            required=True
        )
        
        account_label = ask_question(
            "账号显示名称（可选，默认使用账号ID）",
            default=account_id,
            required=False
        )
        
        storage_path = ask_question(
            "登录状态文件路径",
            default=f".auth/{account_id}-storage-state.json",
            required=True
        )
        
        accounts.append({
            "id": account_id,
            "label": account_label or account_id,
            "storageStatePath": storage_path,
        })
        
        account_num += 1
        
        if not ask_yes_no("\n是否继续添加下一个账号", default="no"):
            break
    
    rich_ui.print_success(f"已配置 {len(accounts)} 个账号。")
    return accounts


def write_env_file(config: dict[str, str]) -> Path:
    """Write .env file to disk."""
    env_path = Path.cwd() / ".env"
    ensure_dir(env_path.parent)
    
    lines = ["# Qwen Transcribe 配置文件", "# 由 init 向导生成", ""]
    
    # Group related settings
    groups = [
        ("服务器配置", ["QWEN_BASE_URL"]),
        ("账号配置", ["QWEN_ACCOUNT", "QWEN_ACCOUNT_STRATEGY"]),
        ("导出配置", ["QWEN_EXPORT_FORMAT", "QWEN_DELETE_AFTER_EXPORT", "QWEN_EXPORT_CONCURRENCY"]),
        ("路径配置", ["QWEN_DOWNLOAD_DIR"]),
    ]
    
    for group_name, keys in groups:
        lines.append(f"# {group_name}")
        for key in keys:
            if key in config:
                lines.append(f"{key}={config[key]}")
        lines.append("")
    
    content = "\n".join(lines)
    env_path.write_text(content, encoding="utf-8")
    return env_path


def write_accounts_file(accounts: list[dict[str, str]]) -> Path | None:
    """Write accounts.json file to disk."""
    if not accounts:
        return None
    
    accounts_path = Path.cwd() / "accounts.json"
    ensure_dir(accounts_path.parent)
    
    content = json.dumps(accounts, indent=2, ensure_ascii=False)
    accounts_path.write_text(content, encoding="utf-8")
    return accounts_path


def print_success_summary(env_path: Path, accounts_path: Path | None) -> None:
    """Print success message and next steps."""
    rich_ui.print_header("✅ 配置完成！", char="✦")
    
    content = f"[bold]📄 环境配置:[/bold] {env_path}"
    if accounts_path:
        content += f"\n[bold]👥 账号配置:[/bold] {accounts_path}"
    else:
        content += "\n[bold]👥 账号配置:[/bold] 未配置（单账号模式）"
    
    rich_ui.print_panel("配置摘要", content, style="green")
    
    rich_ui.print_info("下一步操作:")
    rich_ui.console.print("\n  [bold]1️⃣  登录认证:[/bold]")
    rich_ui.console.print("     [cyan]qwen-transcribe auth[/cyan]")
    if accounts_path:
        accounts_data = json.loads(accounts_path.read_text(encoding="utf-8"))
        if accounts_data:
            rich_ui.console.print(f"     [cyan]qwen-transcribe auth --account {accounts_data[0]['id']}[/cyan]")
    
    rich_ui.console.print("\n  [bold]2️⃣  检查账号状态:[/bold]")
    rich_ui.console.print("     [cyan]qwen-transcribe accounts status[/cyan]")
    
    rich_ui.console.print("\n  [bold]3️⃣  领取配额:[/bold]")
    rich_ui.console.print("     [cyan]qwen-transcribe quota needed[/cyan]")
    
    rich_ui.console.print("\n  [bold]4️⃣  开始转写:[/bold]")
    rich_ui.console.print("     [cyan]qwen-transcribe run <音频/视频文件>[/cyan]")
    
    rich_ui.console.print("\n  [dim]💡 提示: 运行 `qwen-transcribe` 查看所有可用命令[/dim]\n")


async def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    
    # 如果是交互模式，进入向导模式
    if args.interactive:
        return await _run_interactive(args.force)
    
    # 默认模式：快速生成配置
    return await _run_quick(args.force)


async def _run_quick(force: bool = False) -> int:
    """快速生成默认配置"""
    rich_ui.print_header("🚀 Qwen Transcribe 初始化")
    rich_ui.print_info("正在生成默认配置...")
    rich_ui.print_divider()
    
    # 检查现有配置
    env_path = Path.cwd() / ".env"
    accounts_path = Path.cwd() / "accounts.json"
    
    if env_path.exists() or accounts_path.exists():
        if not force:
            files = []
            if env_path.exists():
                files.append(".env")
            if accounts_path.exists():
                files.append("accounts.json")
            
            rich_ui.print_warning(f"发现已存在的配置文件: {', '.join(files)}")
            rich_ui.print_info("使用 --force 参数可强制覆盖")
            return 1
    
    # 生成 .env
    env_config = {
        "QWEN_BASE_URL": "https://www.qianwen.com",
        "QWEN_ACCOUNT": "",
        "QWEN_ACCOUNT_STRATEGY": "round-robin",
        "QWEN_EXPORT_FORMAT": "md",
        "QWEN_DELETE_AFTER_EXPORT": "true",
        "QWEN_DOWNLOAD_DIR": "downloads",
        "QWEN_EXPORT_CONCURRENCY": "2",
    }
    env_path = write_env_file(env_config)
    rich_ui.print_success(f".env 已生成: {env_path}")
    
    # 生成 accounts.json（空数组，单账号模式）
    accounts_path = write_accounts_file([])
    if accounts_path:
        rich_ui.print_success(f"accounts.json 已生成: {accounts_path}")
    
    # 打印下一步指引
    rich_ui.print_divider()
    rich_ui.print_header("✅ 初始化完成！", char="✦")
    
    content = (
        f"[bold]📄 环境配置:[/bold] {env_path}\n"
        f"[bold]👥 账号配置:[/bold] 单账号模式（无需配置）\n\n"
        f"[dim]提示: 如需多账号配置，编辑 accounts.json 或运行:[/dim]\n"
        f"[cyan]qwen-transcribe init --interactive[/cyan]"
    )
    rich_ui.print_panel("配置摘要", content, style="green")
    
    rich_ui.print_info("下一步操作:")
    rich_ui.console.print("\n  [bold]1️⃣  登录认证:[/bold]")
    rich_ui.console.print("     [cyan]qwen-transcribe auth[/cyan]")
    rich_ui.console.print("\n  [bold]2️⃣  检查账号状态:[/bold]")
    rich_ui.console.print("     [cyan]qwen-transcribe accounts status[/cyan]")
    rich_ui.console.print("\n  [bold]3️⃣  开始转写:[/bold]")
    rich_ui.console.print("     [cyan]qwen-transcribe run <音频/视频文件>[/cyan]")
    rich_ui.console.print("\n  [dim]💡 提示: 运行 `qwen-transcribe` 查看所有可用命令[/dim]\n")
    
    return 0


async def _run_interactive(force: bool = False) -> int:
    """交互式向导模式"""
    rich_ui.print_header("🎉 欢迎使用 Qwen Transcribe 配置向导！")
    rich_ui.print_info("此向导将帮助您自定义 .env 和 accounts.json 配置文件。")
    rich_ui.print_divider()
    
    # Check existing config
    env_exists, accounts_exists = check_existing_config(force)
    
    # Setup .env
    env_config = setup_env_config()
    env_path = write_env_file(env_config)
    rich_ui.print_success(f".env 已保存到: {env_path}")
    
    # Setup accounts
    accounts = setup_accounts_config()
    accounts_path = write_accounts_file(accounts)
    if accounts_path:
        rich_ui.print_success(f"accounts.json 已保存到: {accounts_path}")
    
    # Print success message
    print_success_summary(env_path, accounts_path)
    
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
