#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置预设模板 - 提供快速配置模板

3种预设：
- beginner: 最简配置，只需填账号信息
- pro: 启用高级功能（并发、压缩、自动清理）
- server: 适合服务器部署的后台模式
"""

import os
from pathlib import Path

import questionary
from rich.console import Console

console = Console()


PRESETS = {
    "beginner": {
        "name": "🌱 新手模式",
        "description": "最简配置，只需填账号信息，适合首次使用",
        "config": {
            # Pipeline配置
            "PIPELINE_CONCURRENCY": "3",  # 低并发，避免限流
            "PIPELINE_DELETE_AFTER_EXPORT": "true",  # 自动清理云端
            "PIPELINE_REMOVE_VIDEO": "true",  # 自动删除原视频
            "PIPELINE_KEEP_ORIGINAL": "false",
            # 抖音配置
            "DOUYIN_AUTO_COMPRESS": "false",  # 不压缩，保持原画质
            "DOUYIN_MAX_PER_USER": "5",  # 每次只下载少量
        },
        "features": [
            "✅ 基础下载和转写",
            "✅ 自动清理云端记录",
            "✅ 自动删除原视频（省空间）",
            "❌ 不启用视频压缩",
            "❌ 低并发（3路）",
        ]
    },
    "pro": {
        "name": "🚀 专业模式",
        "description": "启用所有高级功能，适合熟练用户",
        "config": {
            # Pipeline配置
            "PIPELINE_CONCURRENCY": "6",  # 高并发
            "PIPELINE_DELETE_AFTER_EXPORT": "true",
            "PIPELINE_REMOVE_VIDEO": "true",
            "PIPELINE_KEEP_ORIGINAL": "false",
            # 抖音配置
            "DOUYIN_AUTO_COMPRESS": "true",  # 启用压缩
            "DOUYIN_COMPRESS_CRF": "32",  # 中等质量
            "DOUYIN_MAX_PER_USER": "20",  # 批量下载
        },
        "features": [
            "✅ 全部功能启用",
            "✅ 6路高并发转写",
            "✅ 自动压缩视频",
            "✅ 自动清理",
            "✅ 批量处理优化",
        ]
    },
    "server": {
        "name": "🖥️ 服务器模式",
        "description": "适合服务器部署，后台运行，无需交互",
        "config": {
            # Pipeline配置
            "PIPELINE_CONCURRENCY": "10",  # 更高并发
            "PIPELINE_DELETE_AFTER_EXPORT": "true",
            "PIPELINE_REMOVE_VIDEO": "true",
            "PIPELINE_KEEP_ORIGINAL": "false",
            # 抖音配置
            "DOUYIN_AUTO_COMPRESS": "true",
            "DOUYIN_COMPRESS_CRF": "28",  # 更好质量
            "DOUYIN_MAX_PER_USER": "50",  # 大量下载
            # 服务器模式特殊配置
            "RUN_HEADLESS": "true",  # 无头模式
            "LOG_LEVEL": "INFO",  # 详细日志
        },
        "features": [
            "✅ 服务器优化配置",
            "✅ 10路超高并发",
            "✅ 无头模式（无需显示器）",
            "✅ 详细日志记录",
            "✅ 适合定时任务",
        ]
    }
}


def apply_preset(preset_name: str, auto_apply: bool = False) -> bool:
    """应用预设配置

    Args:
        preset_name: 预设名称 (beginner/pro/server)
        auto_apply: 是否自动应用，不询问

    Returns:
        是否成功应用
    """
    if preset_name not in PRESETS:
        console.print(f"[red]❌ 未知的预设: {preset_name}[/red]")
        return False

    preset = PRESETS[preset_name]

    # 显示预设信息
    console.print()
    console.print(f"[bold cyan]{preset['name']}[/bold cyan]")
    console.print(f"[dim]{preset['description']}[/dim]")
    console.print()
    console.print("[bold]包含功能:[/bold]")
    for feature in preset["features"]:
        console.print(f"  {feature}")
    console.print()

    # 确认应用
    if not auto_apply:
        confirm = questionary.confirm(
            "是否应用此预设？",
            default=True
        ).ask()

        if not confirm:
            console.print("[yellow]已取消[/yellow]")
            return False

    # 应用环境变量
    for key, value in preset["config"].items():
        os.environ[key] = value
        console.print(f"[green]✓[/green] 设置 {key} = {value}")

    # 创建配置文件
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    # 写入预设标记
    preset_file = config_dir / "active_preset.txt"
    preset_file.write_text(preset_name, encoding="utf-8")

    console.print()
    console.print(f"[bold green]✅ 预设 '{preset_name}' 已应用！[/bold green]")
    console.print(f"[dim]配置已保存到 {preset_file}[/dim]")

    return True


def show_current_preset():
    """显示当前使用的预设"""
    preset_file = Path("config/active_preset.txt")
    if preset_file.exists():
        preset_name = preset_file.read_text(encoding="utf-8").strip()
        if preset_name in PRESETS:
            preset = PRESETS[preset_name]
            console.print(f"\n[bold]当前预设:[/bold] {preset['name']}")
            console.print(f"[dim]{preset['description']}[/dim]\n")
            return

    console.print("[yellow]当前未选择预设[/yellow]\n")


def interactive_preset_wizard():
    """交互式预设选择向导"""
    console.print(Panel(
        "[bold]⚙️  配置预设选择[/bold]\n\n"
        "选择一个适合你的配置模板，快速开始",
        border_style="cyan",
        title="预设向导"
    ))

    show_current_preset()

    choices = [
        questionary.Choice(
            title=PRESETS["beginner"]["name"],
            value="beginner",
            description=PRESETS["beginner"]["description"],
        ),
        questionary.Choice(
            title=PRESETS["pro"]["name"],
            value="pro",
            description=PRESETS["pro"]["description"],
        ),
        questionary.Choice(
            title=PRESETS["server"]["name"],
            value="server",
            description=PRESETS["server"]["description"],
        ),
        questionary.Choice(
            title="⏭️  跳过，使用手动配置",
            value="skip",
        ),
    ]

    choice = questionary.select(
        "选择预设模板:",
        choices=choices,
        default="beginner"
    ).ask()

    if choice == "skip":
        console.print("\n[yellow]已跳过预设，将使用手动配置[/yellow]\n")
        return

    apply_preset(choice)


def create_preset_config_files():
    """创建预设配置文件"""
    presets_dir = Path("config/presets")
    presets_dir.mkdir(parents=True, exist_ok=True)

    for preset_name, preset_data in PRESETS.items():
        # 生成示例配置文件
        example_file = presets_dir / f"{preset_name}.env.example"
        with open(example_file, "w", encoding="utf-8") as f:
            f.write(f"# {preset_data['name']} - 预设配置示例\n")
            f.write(f"# {preset_data['description']}\n\n")
            for key, value in preset_data["config"].items():
                f.write(f"{key}={value}\n")

        console.print(f"[green]✓[/green] 创建 {example_file}")


def main():
    """独立运行预设向导"""
    import argparse
    from rich.panel import Panel

    parser = argparse.ArgumentParser(description="配置预设选择器")
    parser.add_argument("--apply", choices=["beginner", "pro", "server"],
                       help="直接应用指定预设，不显示向导")
    parser.add_argument("--list", action="store_true",
                       help="列出所有预设")
    parser.add_argument("--show", action="store_true",
                       help="显示当前预设")
    parser.add_argument("--create-files", action="store_true",
                       help="创建预设配置文件")

    args = parser.parse_args()

    if args.apply:
        apply_preset(args.apply, auto_apply=True)
    elif args.list:
        console.print("[bold]📋 可用预设:[/bold]\n")
        for name, data in PRESETS.items():
            console.print(f"[bold]{data['name']}[/bold] ({name})")
            console.print(f"[dim]{data['description']}[/dim]")
            console.print()
    elif args.show:
        show_current_preset()
    elif args.create_files:
        create_preset_config_files()
    else:
        interactive_preset_wizard()


if __name__ == "__main__":
    main()
