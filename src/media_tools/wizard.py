#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首次使用向导 - 3步快速配置向导

帮助用户在5分钟内完成初始配置并开始使用核心功能
"""

import os
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def check_first_run() -> bool:
    """检测是否首次运行"""
    marker = Path(".config_initialized")
    return not marker.exists()


def mark_config_initialized():
    """标记配置已完成"""
    Path(".config_initialized").write_text("true", encoding="utf-8")
    console.print("\n✅ [green]配置已保存！下次启动将直接进入主菜单[/green]")


def show_welcome():
    """显示欢迎信息"""
    console.print()
    console.print(Panel.fit(
        "[bold blue]🎬 欢迎使用 Media Tools 创作助手！[/bold blue]\n\n"
        "专为自媒体创作者打造的全自动工具\n"
        "一键完成：视频下载 → AI转写 → 文稿输出\n\n"
        "[yellow]只需3步，5分钟快速开始！[/yellow]",
        border_style="blue"
    ))
    console.print()


def step1_choose_scenario() -> str:
    """步骤1: 选择使用场景"""
    console.print(Panel(
        "[bold]📋 步骤 1/3: 选择你的使用场景[/bold]\n\n"
        "这将帮你自动配置最合适的功能",
        border_style="cyan",
        title="场景选择"
    ))

    scenario = questionary.select(
        "你最主要的用途是？",
        choices=[
            questionary.Choice(
                title="🔄 全自动流水线 (推荐)",
                value="auto",
                description="下载视频 → 自动转写 → 输出文稿，一条链全自动",
            ),
            questionary.Choice(
                title="📥 主要下载视频",
                value="download",
                description="批量下载抖音视频到本地，暂不转写",
            ),
            questionary.Choice(
                title="🎙️ 主要转写本地视频",
                value="transcribe",
                description="已有视频文件，只需AI转写成文稿",
            ),
        ],
        default="auto"
    ).ask()

    if scenario is None:
        console.print("\n[yellow]已取消配置[/yellow]")
        return None

    console.print(f"\n✅ 已选择: [green]{scenario}[/green]\n")
    return scenario


def step2_account_setup(scenario: str):
    """步骤2: 账号配置引导"""
    console.print(Panel(
        "[bold]🔑 步骤 2/3: 账号配置[/bold]\n\n"
        "需要配置相关账号认证才能使用功能",
        border_style="cyan",
        title="账号配置"
    ))

    auth_actions = []

    # 根据场景决定推荐配置
    if scenario in ["auto", "download"]:
        auth_actions.append("douyin")

    if scenario in ["auto", "transcribe"]:
        auth_actions.append("qwen")

    if not auth_actions:
        return

    choice = questionary.select(
        "现在要配置哪个账号？",
        choices=[
            questionary.Choice(
                title="📱 抖音账号 (扫码登录)",
                value="douyin",
                description="用于下载抖音视频",
                checked="douyin" in auth_actions,
            ),
            questionary.Choice(
                title="🤖 Qwen AI账号 (浏览器认证)",
                value="qwen",
                description="用于AI转写",
                checked="qwen" in auth_actions,
            ),
            questionary.Choice(
                title="⏭️  跳过，稍后配置",
                value="skip",
            ),
        ]
    ).ask()

    if choice == "skip":
        console.print("\n⏭️  稍后可通过主菜单的'设置与管理'进行配置\n")
        return
    elif choice == "douyin":
        console.print("\n🔐 正在启动抖音扫码登录...")
        try:
            from scripts.core.auth import login_sync
            success, msg = login_sync(persist=True)
            if success:
                console.print("✅ [green]抖音认证成功！[/green]\n")
            else:
                console.print(f"❌ [red]登录失败: {msg}[/red]\n")
                console.print("[yellow]💡 提示: 稍后可通过 '设置 → 抖音认证' 重试[/yellow]\n")
        except Exception as e:
            console.print(f"❌ [red]登录过程出错: {e}[/red]\n")
    elif choice == "qwen":
        console.print("\n🔐 正在启动Qwen AI认证...")
        try:
            from src.media_tools.transcribe.cli.auth import run_auth
            run_auth()
            console.print("✅ [green]Qwen认证成功！[/green]\n")
        except Exception as e:
            console.print(f"❌ [red]认证过程出错: {e}[/red]\n")
            console.print("[yellow]💡 提示: 稍后可通过 '设置 → Qwen认证' 重试[/yellow]\n")


def step3_test_run(scenario: str):
    """步骤3: 完成并测试"""
    console.print(Panel(
        "[bold]🎉 步骤 3/3: 配置完成！[/bold]\n\n"
        "现在可以开始使用了！",
        border_style="green",
        title="完成"
    ))

    console.print("\n[bold]📋 你的配置摘要:[/bold]")
    console.print(f"  • 使用场景: {scenario}")
    console.print(f"  • 配置状态: ✅ 已初始化")
    console.print()

    action = questionary.select(
        "接下来要做什么？",
        choices=[
            questionary.Choice("🚀 直接进入主菜单开始使用", value="menu"),
            questionary.Choice("🧪 运行一个测试任务", value="test"),
            questionary.Choice("📖 查看使用教程", value="tutorial"),
        ]
    ).ask()

    if action == "test":
        console.print("\n[bold]🧪 测试任务[/bold]\n")
        console.print("请选择测试类型:")
        test_type = questionary.select(
            "测试类型",
            choices=[
                questionary.Choice("📥 下载测试（需要抖音认证）", value="download"),
                questionary.Choice("🎙️ 转写测试（需要Qwen认证）", value="transcribe"),
                questionary.Choice("⏭️  跳过测试", value="skip"),
            ]
        ).ask()

        if test_type == "download":
            console.print("\n💡 [yellow]下载测试需要提供一个抖音视频链接[/yellow]")
            url = input("请输入视频链接 (或直接回车跳过): ").strip()
            if url:
                console.print("\n🔄 开始测试下载...")
                try:
                    from scripts.core.downloader import download_by_url
                    result = download_by_url(url, max_counts=1)
                    if result:
                        console.print("✅ [green]下载测试成功！[/green]\n")
                    else:
                        console.print("❌ [red]下载测试失败[/red]\n")
                except Exception as e:
                    console.print(f"❌ [red]测试出错: {e}[/red]\n")
            else:
                console.print("\n⏭️  跳过测试\n")

        elif test_type == "transcribe":
            console.print("\n💡 [yellow]转写测试需要一个视频文件[/yellow]")
            console.print("💡 请先下载或准备一个MP4文件，稍后手动测试\n")

    elif action == "tutorial":
        console.print(Panel(
            "[bold]📖 快速使用教程[/bold]\n\n"
            "**主菜单说明：**\n\n"
            "• 🚀 **快速开始** - 你最常用的功能\n"
            "  - 选项1: 输入链接，一键下载+转写\n"
            "  - 选项2: 批量处理关注列表\n\n"
            "• 🛠️ **高级功能** - 进阶操作\n"
            "  - 视频下载、压缩、数据看板等\n\n"
            "• ⚙️ **设置与管理** - 配置维护\n"
            "  - 账号认证、配置中心、数据清理等\n\n"
            "**小贴士：**\n"
            "1. 首次使用建议先从'快速开始'体验\n"
            "2. 遇到问题随时查看 README.md 文档\n"
            "3. 配置保存在 config/ 目录下，可随时修改",
            border_style="blue",
            title="教程"
        ))

    # 标记配置完成
    mark_config_initialized()


def run_wizard():
    """运行完整的配置向导"""
    show_welcome()

    # 步骤1: 选择场景
    scenario = step1_choose_scenario()
    if scenario is None:
        return

    # 步骤2: 账号配置
    step2_account_setup(scenario)

    # 步骤3: 完成
    step3_test_run(scenario)

    console.print("\n" + "="*60)
    console.print("[bold green]🎉 恭喜！配置完成，开始创作吧！[/bold green]")
    console.print("="*60 + "\n")


def main():
    """独立运行向导"""
    if check_first_run():
        console.print("[yellow]检测到首次使用，启动配置向导...[/yellow]\n")
        run_wizard()
    else:
        console.print("[green]✅ 已完成配置，直接进入主菜单[/green]\n")
        from cli import main_menu
        main_menu()


if __name__ == "__main__":
    main()
