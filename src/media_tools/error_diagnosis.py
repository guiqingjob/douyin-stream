#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误诊断与解决建议模块

功能：
- 根据错误类型提供详细的解决建议
- 自动诊断常见问题
- 提供一键修复方案
"""

from enum import Enum
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "网络错误"
    AUTH = "认证错误"
    QUOTA = "配额错误"
    FILE = "文件错误"
    CONFIG = "配置错误"
    API = "API错误"
    PERMISSION = "权限错误"
    UNKNOWN = "未知错误"


SOLUTIONS = {
    ErrorCategory.NETWORK: {
        "title": "🌐 网络错误诊断",
        "diagnosis": [
            "检查网络连接是否正常",
            "检查是否能访问抖音/Qwen网站",
            "检查防火墙是否阻止了连接",
        ],
        "solutions": [
            "尝试更换网络环境（WiFi → 手机热点）",
            "检查代理设置：`echo $http_proxy`",
            "等待几分钟后重试（可能是临时故障）",
            "使用 `ping douyin.com` 测试连通性",
        ],
        "auto_fix": "运行网络诊断测试连通性",
    },
    ErrorCategory.AUTH: {
        "title": "🔑 认证错误诊断",
        "diagnosis": [
            "Cookie或认证信息已过期",
            "认证信息未正确配置",
            "登录状态失效",
        ],
        "solutions": [
            "重新进行扫码登录",
            "检查 config/config.yaml 中的 cookie 配置",
            "检查 .auth/ 目录下的认证文件",
            "抖音Cookie有效期约为24小时，需定期更新",
        ],
        "auto_fix": "启动扫码登录流程",
    },
    ErrorCategory.QUOTA: {
        "title": "📊 配额错误诊断",
        "diagnosis": [
            "Qwen AI配额已用尽",
            "当月配额已耗尽",
            "需要领取新配额",
        ],
        "solutions": [
            "运行 `qwt quota claim` 领取新配额",
            "检查配额使用：`qwt quota status`",
            "等待下个月配额重置",
            "考虑使用其他AI服务（如讯飞、OpenAI）",
        ],
        "auto_fix": "自动尝试领取配额",
    },
    ErrorCategory.FILE: {
        "title": "📁 文件错误诊断",
        "diagnosis": [
            "文件不存在或路径错误",
            "文件格式不支持",
            "文件损坏",
        ],
        "solutions": [
            "检查文件路径是否正确",
            "确认文件格式为 MP4/M4A/WAV/MP3",
            "尝试重新下载文件",
            "检查磁盘空间是否充足",
        ],
        "auto_fix": None,
    },
    ErrorCategory.CONFIG: {
        "title": "⚙️  配置错误诊断",
        "diagnosis": [
            "配置文件缺失或格式错误",
            "环境变量未正确设置",
            "配置参数不合法",
        ],
        "solutions": [
            "运行配置预设：`python -m src.media_tools.config_presets --apply beginner`",
            "检查 config/ 目录下的配置文件",
            "重新运行首次使用向导",
            "参考 config/*.example 模板文件",
        ],
        "auto_fix": "应用默认配置预设",
    },
    ErrorCategory.API: {
        "title": "🔌 API错误诊断",
        "diagnosis": [
            "第三方API接口变更或不可用",
            "API限流或封禁",
            "接口版本过期",
        ],
        "solutions": [
            "检查抖音API是否有更新（F2框架可能需要更新）",
            "检查Qwen AI服务状态",
            "等待API恢复或联系服务商",
            "查看项目GitHub Issues是否有类似问题",
        ],
        "auto_fix": None,
    },
    ErrorCategory.PERMISSION: {
        "title": "🔒 权限错误诊断",
        "diagnosis": [
            "文件/目录权限不足",
            "需要管理员权限",
            "磁盘只读",
        ],
        "solutions": [
            "检查文件权限：`ls -la <file>`",
            "使用 `chmod` 修改权限",
            "确保对下载/转写目录有读写权限",
            "避免在系统目录操作",
        ],
        "auto_fix": None,
    },
    ErrorCategory.UNKNOWN: {
        "title": "❓ 未知错误诊断",
        "diagnosis": [
            "错误类型无法识别",
            "可能是程序bug",
        ],
        "solutions": [
            "查看详细错误日志",
            "查看 logs/ 目录下的日志文件",
            "提交Issue到GitHub，附上错误日志",
            "尝试重新安装依赖",
        ],
        "auto_fix": None,
    },
}


def classify_error(error_message: str, exception: Exception = None) -> ErrorCategory:
    """根据错误消息分类错误类型"""
    error_lower = error_message.lower()

    # 网络错误
    if any(kw in error_lower for kw in [
        "network", "timeout", "connection", "connect",
        "网络", "超时", "连接", "refused"
    ]):
        return ErrorCategory.NETWORK

    # 认证错误
    if any(kw in error_lower for kw in [
        "auth", "login", "cookie", "token", "credential",
        "认证", "登录", "过期", "expired", "unauthorized"
    ]):
        return ErrorCategory.AUTH

    # 配额错误
    if any(kw in error_lower for kw in [
        "quota", "limit", "exceeded", "exhausted",
        "配额", "限额", "用完"
    ]):
        return ErrorCategory.QUOTA

    # 文件错误
    if any(kw in error_lower for kw in [
        "file", "not found", "no such", "path",
        "文件", "不存在", "路径"
    ]):
        return ErrorCategory.FILE

    # 配置错误
    if any(kw in error_lower for kw in [
        "config", "configuration", "env", "environment",
        "配置", "环境变量"
    ]):
        return ErrorCategory.CONFIG

    # API错误
    if any(kw in error_lower for kw in [
        "api", "endpoint", "404", "500", "502", "503",
        "接口", "服务"
    ]):
        return ErrorCategory.API

    # 权限错误
    if any(kw in error_lower for kw in [
        "permission", "denied", "access", "readonly",
        "权限", "拒绝"
    ]):
        return ErrorCategory.PERMISSION

    return ErrorCategory.UNKNOWN


def diagnose_and_suggest(
    error_message: str,
    exception: Exception = None,
    category: ErrorCategory = None,
) -> Panel:
    """诊断错误并提供解决建议

    Args:
        error_message: 错误消息
        exception: 异常对象（可选）
        category: 错误分类（可选，不传则自动分类）

    Returns:
        Rich Panel 对象，包含诊断信息
    """
    if category is None:
        category = classify_error(error_message, exception)

    solution = SOLUTIONS[category]

    # 构建诊断信息
    content = []
    content.append(f"[bold]{solution['title']}[/bold]\n")

    content.append("[bold]🔍 可能原因:[/bold]\n")
    for i, reason in enumerate(solution["diagnosis"], 1):
        content.append(f"  {i}. {reason}")
    content.append("")

    content.append("[bold]💡 解决方案:[/bold]\n")
    for i, sol in enumerate(solution["solutions"], 1):
        content.append(f"  {i}. {sol}")
    content.append("")

    if solution["auto_fix"]:
        content.append(f"[bold yellow]🔧 自动修复:[/bold yellow] {solution['auto_fix']}")

    # 原始错误
    content.append(f"\n[dim]原始错误: {error_message[:100]}[/dim]")

    return Panel(
        "\n".join(content),
        border_style="yellow",
        title="🩺 错误诊断"
    )


def auto_fix_error(category: ErrorCategory) -> bool:
    """尝试自动修复错误

    Returns:
        是否修复成功
    """
    if category == ErrorCategory.AUTH:
        console.print("\n🔧 正在启动认证修复...\n")
        try:
            # 尝试抖音认证
            from scripts.core.auth import login_sync
            success, msg = login_sync(persist=True)
            if success:
                console.print("[green]✅ 抖音认证修复成功！[/green]\n")
                return True

            # 尝试Qwen认证
            console.print("尝试Qwen AI认证...\n")
            from src.media_tools.transcribe.cli.auth import run_auth
            run_auth()
            console.print("[green]✅ Qwen认证修复成功！[/green]\n")
            return True
        except Exception as e:
            console.print(f"[red]❌ 认证修复失败: {e}[/red]\n")
            return False

    elif category == ErrorCategory.QUOTA:
        console.print("\n🔧 正在尝试领取配额...\n")
        try:
            from src.media_tools.transcribe.cli.claim_equity import run_claim
            run_claim(all=True)
            console.print("[green]✅ 配额领取成功！[/green]\n")
            return True
        except Exception as e:
            console.print(f"[red]❌ 配额领取失败: {e}[/red]\n")
            return False

    elif category == ErrorCategory.CONFIG:
        console.print("\n🔧 正在应用默认配置预设...\n")
        try:
            from src.media_tools.config_presets import apply_preset
            apply_preset("beginner", auto_apply=True)
            console.print("[green]✅ 配置预设应用成功！[/green]\n")
            return True
        except Exception as e:
            console.print(f"[red]❌ 配置应用失败: {e}[/red]\n")
            return False

    else:
        console.print(f"\n[yellow]⚠️  {category.value}暂无自动修复方案，请手动解决[/yellow]\n")
        return False


def run_diagnostic() -> dict:
    """运行全面诊断检查

    Returns:
        诊断结果字典
    """
    console.print("[bold]🔍 运行全面诊断检查...[/bold]\n")

    results = {
        "network": False,
        "auth_douyin": False,
        "auth_qwen": False,
        "config": False,
        "disk_space": False,
        "dependencies": False,
    }

    # 1. 网络检查
    console.print("1. 检查网络连接...")
    try:
        import urllib.request
        urllib.request.urlopen("https://douyin.com", timeout=5)
        console.print("   [green]✓ 抖音可访问[/green]")
        results["network"] = True
    except Exception as e:
        console.print(f"   [red]✗ 抖音不可访问: {e}[/red]")

    # 2. 抖音认证检查
    console.print("\n2. 检查抖音认证...")
    try:
        from scripts.core.config_mgr import get_config
        config = get_config()
        cookie = config.get_cookie()
        if cookie and len(cookie) > 100:
            console.print("   [green]✓ Cookie已配置[/green]")
            results["auth_douyin"] = True
        else:
            console.print("   [red]✗ Cookie未配置或无效[/red]")
    except Exception as e:
        console.print(f"   [red]✗ 检查出错: {e}[/red]")

    # 3. Qwen认证检查
    console.print("\n3. 检查Qwen认证...")
    auth_file = Path(".auth/playwright_state.json")
    if auth_file.exists():
        console.print(f"   [green]✓ 认证文件存在: {auth_file}[/green]")
        results["auth_qwen"] = True
    else:
        console.print("   [yellow]⚠  认证文件不存在[/yellow]")

    # 4. 配置检查
    console.print("\n4. 检查配置文件...")
    config_files = [
        Path("config/config.yaml"),
    ]
    missing = [f for f in config_files if not f.exists()]
    if not missing:
        console.print("   [green]✓ 配置文件齐全[/green]")
        results["config"] = True
    else:
        console.print(f"   [red]✗ 缺失配置: {', '.join(str(f) for f in missing)}[/red]")

    # 5. 磁盘空间检查
    console.print("\n5. 检查磁盘空间...")
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024**3)
        if free_gb > 1:
            console.print(f"   [green]✓ 可用空间: {free_gb:.1f} GB[/green]")
            results["disk_space"] = True
        else:
            console.print(f"   [red]✗ 可用空间不足: {free_gb:.1f} GB[/red]")
    except Exception as e:
        console.print(f"   [red]✗ 检查出错: {e}[/red]")

    # 6. 依赖检查
    console.print("\n6. 检查依赖安装...")
    try:
        import f2
        import playwright
        import rich
        import questionary
        console.print("   [green]✓ 所有依赖已安装[/green]")
        results["dependencies"] = True
    except ImportError as e:
        console.print(f"   [red]✗ 缺少依赖: {e}[/red]")

    # 总结
    passed = sum(results.values())
    total = len(results)

    console.print(f"\n[bold]诊断结果: {passed}/{total} 通过[/bold]\n")

    if passed == total:
        console.print("[green]✅ 一切正常！[/green]\n")
    else:
        console.print("[yellow]⚠️  发现问题，请按上述建议修复[/yellow]\n")

    return results


def main():
    """独立运行诊断"""
    import argparse

    parser = argparse.ArgumentParser(description="错误诊断与解决")
    parser.add_argument("--full", action="store_true",
                       help="运行全面诊断检查")
    parser.add_argument("--error", type=str,
                       help="诊断指定错误消息")

    args = parser.parse_args()

    if args.full:
        run_diagnostic()
    elif args.error:
        category = classify_error(args.error)
        panel = diagnose_and_suggest(args.error, category=category)
        console.print(panel)

        # 询问是否自动修复
        try:
            fix = input("\n是否尝试自动修复？(y/N): ").strip().lower()
            if fix == "y":
                auto_fix_error(category)
        except (EOFError, KeyboardInterrupt):
            pass
    else:
        console.print(Panel(
            "[bold]🩺 错误诊断工具[/bold]\n\n"
            "用法:\n"
            "  --full          运行全面诊断检查\n"
            "  --error '消息'  诊断指定错误\n\n"
            "示例:\n"
            "  python -m src.media_tools.error_diagnosis --full\n"
            "  python -m src.media_tools.error_diagnosis --error 'Connection timeout'",
            border_style="blue"
        ))


if __name__ == "__main__":
    main()
