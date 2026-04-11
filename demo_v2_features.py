#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 新功能演示脚本

运行此脚本可体验所有新增功能：
- 首次使用向导
- 配置预设
- 统计面板
- 错误诊断
- 配置管理
- 进度可视化
- 批量报告
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import time

console = Console()


def show_title(title: str, desc: str = ""):
    """显示标题"""
    console.print()
    console.print("=" * 70)
    console.print(f"[bold cyan]{title}[/bold cyan]")
    if desc:
        console.print(f"[dim]{desc}[/dim]")
    console.print("=" * 70)
    console.print()


def demo_wizard():
    """演示首次使用向导"""
    show_title("🧙 首次使用向导", "3步快速配置，5分钟上手")

    console.print(Panel(
        "[bold]步骤 1/3: 选择使用场景[/bold]\n\n"
        "• 🔄 全自动流水线（推荐）\n"
        "• 📥 主要下载视频\n"
        "• 🎙️ 主要转写本地视频",
        border_style="cyan",
        title="场景选择"
    ))

    console.print("\n[dim]→ 用户选择'全自动流水线'[/dim]\n")

    console.print(Panel(
        "[bold]步骤 2/3: 账号配置[/bold]\n\n"
        "• 📱 抖音扫码登录\n"
        "• 🤖 Qwen AI认证\n"
        "• ⏭️  跳过，稍后配置",
        border_style="cyan",
        title="账号配置"
    ))

    console.print("\n[dim]→ 用户选择'抖音扫码登录'并完成认证[/dim]\n")

    console.print(Panel(
        "[bold]步骤 3/3: 配置完成！[/bold]\n\n"
        "✅ 已选择: 全自动流水线\n"
        "✅ 抖音认证: 已配置\n"
        "\n接下来可以：\n"
        "• 🚀 直接进入主菜单\n"
        "• 🧪 运行测试任务\n"
        "• 📖 查看使用教程",
        border_style="green",
        title="完成"
    ))

    console.print("\n[green]✅ 向导演示完成！[/green]\n")
    time.sleep(1)


def demo_presets():
    """演示配置预设"""
    show_title("⚙️  配置预设模板", "3种预设，一键应用")

    console.print("[bold]可用预设:[/bold]\n")

    console.print(Panel(
        "[bold]🌱 新手模式 (beginner)[/bold]\n\n"
        "• 低并发（3路）\n"
        "• 自动清理\n"
        "• 最简配置\n"
        "• 只需填账号信息",
        border_style="green",
        title="预设 1/3"
    ))

    console.print(Panel(
        "[bold]🚀 专业模式 (pro)[/bold]\n\n"
        "• 6路高并发\n"
        "• 自动压缩\n"
        "• 全部功能启用\n"
        "• 适合熟练用户",
        border_style="blue",
        title="预设 2/3"
    ))

    console.print(Panel(
        "[bold]🖥️  服务器模式 (server)[/bold]\n\n"
        "• 10路超高并发\n"
        "• 无头模式\n"
        "• 详细日志\n"
        "• 适合定时任务",
        border_style="magenta",
        title="预设 3/3"
    ))

    console.print("\n[dim]→ 运行命令应用预设:[/dim]")
    console.print("  python -m src.media_tools.config_presets --apply beginner\n")
    time.sleep(1)


def demo_stats():
    """演示统计面板"""
    show_title("📊 创作数据统计", "了解你的创作效率")

    console.print(Panel(
        "[bold]📊 创作数据统计[/bold]\n\n"
        "📅 使用天数      30 天\n"
        "📥 下载视频      156 个\n"
        "📝 转写文稿      142 篇\n"
        "📈 总转写字数    385,234 字\n"
        "⏱️  估算节省时间  42.5 小时\n"
        "👥 关注创作者    15 位",
        border_style="blue",
        title="统计摘要"
    ))

    console.print("\n[bold]🏆 热门创作者 TOP 3[/bold]\n")

    console.print("  🥇 博主A    35个视频    12,450字")
    console.print("  🥈 博主B    28个视频    9,870字")
    console.print("  🥉 博主C    22个视频    7,234字")

    console.print("\n[dim]→ 运行命令查看:[/dim]")
    console.print("  python -m src.media_tools.stats_panel --scan\n")
    time.sleep(1)


def demo_progress():
    """演示进度面板"""
    show_title("📈 任务进度可视化", "实时进度，不再盲目等待")

    console.print(Panel(
        "[bold]📊 统计[/bold]\n\n"
        "  总计: 5 | [green]成功: 3[/green] | [red]失败: 1[/red] | [yellow]跳过: 0[/yellow]\n"
        "  处理中: 1\n"
        "  已用时间: 12.5s\n"
        "  预估剩余: 4.2s",
        border_style="cyan"
    ))

    console.print("\n[bold]任务详情:[/bold]\n")
    console.print("  1. ✅ video_1.mp4    2.1s")
    console.print("  2. ✅ video_2.mp4    2.3s")
    console.print("  3. ✅ video_3.mp4    1.9s")
    console.print("  4. 🔄 video_4.mp4    处理中...")
    console.print("  5. ❌ video_5.mp4    网络错误\n")

    console.print("[dim]→ 使用ProgressPanel类实现[/dim]\n")
    time.sleep(1)


def demo_diagnosis():
    """演示错误诊断"""
    show_title("🩺 智能错误诊断", "错误不再可怕，每个错误都有解决建议")

    console.print(Panel(
        "[bold]🩺 错误诊断[/bold]\n\n"
        "[bold]🌐 网络错误诊断[/bold]\n\n"
        "🔍 可能原因:\n"
        "  1. 网络连接不稳定\n"
        "  2. 代理设置问题\n"
        "  3. 防火墙阻止\n\n"
        "💡 解决方案:\n"
        "  1. 尝试更换网络环境\n"
        "  2. 检查代理设置\n"
        "  3. 等待几分钟后重试\n\n"
        "🔧 自动修复: 运行网络诊断测试连通性",
        border_style="yellow"
    ))

    console.print("\n[dim]→ 运行命令诊断:[/dim]")
    console.print("  python -m src.media_tools.error_diagnosis --full\n")
    time.sleep(1)


def demo_config_manager():
    """演示配置管理"""
    show_title("💾 统一配置管理", "安全、可靠、易用")

    console.print("[bold]配置文件状态:[/bold]\n")

    console.print("  ✓ 抖音配置        config/config.yaml")
    console.print("  ✓ 关注列表        config/following.json")
    console.print("  ✓ 转写环境变量    config/transcribe/.env")
    console.print("  ✗ 转写账号配置    config/transcribe/accounts.json (不存在)")

    console.print("\n[bold]功能列表:[/bold]\n")
    console.print("  • 🔍 验证所有配置")
    console.print("  • 💾 备份/恢复配置")
    console.print("  • 📤 导出/导入配置")
    console.print("  • 🔧 自动修复常见问题")

    console.print("\n[dim]→ 运行命令管理:[/dim]")
    console.print("  python -m src.media_tools.config_manager --interactive\n")
    time.sleep(1)


def demo_batch_report():
    """演示批量报告"""
    show_title("📋 批量操作报告", "详细的执行分析")

    console.print(Panel(
        "[bold]📊 批量操作摘要[/bold]\n\n"
        "  操作名称    批量转写测试\n"
        "  总任务数    5\n"
        "  成功        [green]4[/green]\n"
        "  失败        [red]1[/red]\n"
        "  跳过        [yellow]0[/yellow]\n"
        "  成功率      80.0%\n"
        "  总耗时      10.5s\n"
        "  平均耗时    2.1s/个",
        border_style="blue"
    ))

    console.print("\n[bold red]❌ 错误类型分布:[/bold red]\n")
    console.print("  网络错误    1    100.0%")

    console.print("\n[dim]→ 使用BatchReport类生成[/dim]\n")
    time.sleep(1)


def demo_all_features():
    """演示所有功能"""
    console.print()
    console.print(Panel.fit(
        "[bold blue]🎬 Media Tools V2 新功能演示[/bold blue]\n\n"
        "本脚本将演示所有V2新增功能",
        border_style="blue"
    ))

    # 演示各个功能
    demo_wizard()
    demo_presets()
    demo_stats()
    demo_progress()
    demo_diagnosis()
    demo_config_manager()
    demo_batch_report()

    # 总结
    show_title("🎉 演示完成！", "V2版本更智能、更友好、更强大")

    console.print(Panel(
        "[bold]V2 核心改进:[/bold]\n\n"
        "✅ 首次使用向导 - 5分钟上手\n"
        "✅ 配置预设模板 - 3种预设一键应用\n"
        "✅ 创作数据统计 - 了解你的效率\n"
        "✅ 任务进度可视化 - 实时进度\n"
        "✅ 智能错误诊断 - 解决建议\n"
        "✅ 统一配置管理 - 备份/恢复\n"
        "✅ 批量操作报告 - 详细分析\n"
        "✅ 增强版Pipeline - 重试+断点续传",
        border_style="green",
        title="总结"
    ))

    console.print("\n[bold]下一步:[/bold]\n")
    console.print("  1. 运行 python cli_v2.py 开始使用")
    console.print("  2. 阅读 README_V2.md 了解详情")
    console.print("  3. 查看 PRODUCT_DESIGN_PLAN.md 了解设计思路")
    console.print()


if __name__ == "__main__":
    demo_all_features()
