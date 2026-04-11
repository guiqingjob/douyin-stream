#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目健康检查脚本 - 全面检查项目状态

检查项目：
- 依赖安装
- 配置文件
- 认证状态
- 磁盘空间
- 数据库完整性
- 日志状态
- Git状态
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self.project_root = Path(".")
        self.checks = []  # [{name, status, message}]

    def add_check(self, name: str, status: bool, message: str = ""):
        """添加检查结果"""
        self.checks.append({
            "name": name,
            "status": status,
            "message": message,
        })

    def check_dependencies(self):
        """检查依赖安装"""
        console.print("\n[bold]📦 检查依赖安装...[/bold]\n")

        required_packages = [
            ("rich", "终端美化"),
            ("questionary", "交互选择"),
            ("pyyaml", "YAML解析"),
            ("playwright", "浏览器自动化"),
            ("f2", "抖音下载"),
        ]

        all_ok = True
        for package, desc in required_packages:
            try:
                __import__(package.replace("-", "_"))
                console.print(f"  [green]✓[/green] {package:15s} - {desc}")
            except ImportError:
                console.print(f"  [red]✗[/red] {package:15s} - [red]未安装[/red]")
                all_ok = False

        self.add_check("依赖安装", all_ok, "所有依赖已安装" if all_ok else "部分依赖缺失")

    def check_config_files(self):
        """检查配置文件"""
        console.print("\n[bold]📋 检查配置文件...[/bold]\n")

        config_files = {
            "config/config.yaml": "抖音配置",
            "config/following.json": "关注列表",
            "config/transcribe/.env": "转写环境变量",
        }

        all_ok = True
        for file_path, desc in config_files.items():
            path = Path(file_path)
            if path.exists():
                size = path.stat().st_size
                console.print(f"  [green]✓[/green] {file_path:35s} - {size} bytes")
            else:
                console.print(f"  [red]✗[/red] {file_path:35s} - [red]不存在[/red]")
                all_ok = False

        self.add_check("配置文件", all_ok, "配置文件完整" if all_ok else "部分配置缺失")

    def check_auth_status(self):
        """检查认证状态"""
        console.print("\n[bold]🔑 检查认证状态...[/bold]\n")

        # 抖音认证
        config_file = Path("config/config.yaml")
        douyin_auth = False
        if config_file.exists():
            content = config_file.read_text(encoding="utf-8")
            if "cookie" in content and len(content) > 500:
                douyin_auth = True

        if douyin_auth:
            console.print("  [green]✓[/green] 抖音认证: 已配置")
        else:
            console.print("  [yellow]⚠️  抖音认证: 未配置或Cookie过期[/yellow]")

        # Qwen认证
        auth_file = Path(".auth/playwright_state.json")
        if auth_file.exists():
            console.print("  [green]✓[/green] Qwen认证: 已配置")
            qwen_auth = True
        else:
            console.print("  [yellow]⚠️  Qwen认证: 未配置[/yellow]")
            qwen_auth = False

        self.add_check("认证状态", douyin_auth or qwen_auth, "至少一个认证已配置")

    def check_disk_space(self):
        """检查磁盘空间"""
        console.print("\n[bold]💾 检查磁盘空间...[/bold]\n")

        try:
            total, used, free = shutil.disk_usage(".")
            free_gb = free / (1024**3)

            if free_gb > 5:
                console.print(f"  [green]✓[/green] 可用空间: {free_gb:.1f} GB")
                self.add_check("磁盘空间", True, f"可用 {free_gb:.1f} GB")
            elif free_gb > 1:
                console.print(f"  [yellow]⚠️  可用空间: {free_gb:.1f} GB (较低)[/yellow]")
                self.add_check("磁盘空间", True, f"可用 {free_gb:.1f} GB (较低)")
            else:
                console.print(f"  [red]✗[/red] 可用空间: {free_gb:.1f} GB (不足)[/red]")
                self.add_check("磁盘空间", False, f"可用 {free_gb:.1f} GB (不足)")
        except Exception as e:
            console.print(f"  [red]✗[/red] 检查失败: {e}")
            self.add_check("磁盘空间", False, str(e))

    def check_database(self):
        """检查数据库"""
        console.print("\n[bold]🗄️  检查数据库...[/bold]\n")

        db_file = Path("douyin_users.db")
        if db_file.exists():
            size = db_file.stat().st_size
            console.print(f"  [green]✓[/green] 数据库文件: {size / 1024:.1f} KB")

            # 尝试查询
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                console.print(f"  [green]✓[/green] 数据表数量: {len(tables)}")
                conn.close()
                self.add_check("数据库", True, f"{len(tables)} 个表")
            except Exception as e:
                console.print(f"  [red]✗[/red] 数据库查询失败: {e}")
                self.add_check("数据库", False, str(e))
        else:
            console.print("  [yellow]⚠️  数据库文件不存在 (首次运行后创建)[/yellow]")
            self.add_check("数据库", True, "不存在 (正常)")

    def check_logs(self):
        """检查日志状态"""
        console.print("\n[bold]📝 检查日志状态...[/bold]\n")

        logs_dir = Path("logs")
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            console.print(f"  [green]✓[/green] 日志目录: {len(log_files)} 个文件")
            self.add_check("日志系统", True, f"{len(log_files)} 个日志文件")
        else:
            console.print("  [yellow]⚠️  日志目录不存在 (首次运行后创建)[/yellow]")
            self.add_check("日志系统", True, "不存在 (正常)")

    def check_git_status(self):
        """检查Git状态"""
        console.print("\n[bold]🔧 检查Git状态...[/bold]\n")

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                if not result.stdout.strip():
                    console.print("  [green]✓[/green] 工作区: 干净")
                else:
                    changes = len(result.stdout.strip().split("\n"))
                    console.print(f"  [yellow]⚠️  工作区: {changes} 个未提交更改[/yellow]")

                self.add_check("Git状态", True, "工作区正常")
            else:
                console.print("  [yellow]⚠️  不是Git仓库[/yellow]")
                self.add_check("Git状态", True, "非Git仓库")
        except Exception as e:
            console.print(f"  [yellow]⚠️  Git检查失败: {e}[/yellow]")
            self.add_check("Git状态", True, "检查失败")

    def run_all_checks(self) -> bool:
        """运行所有检查

        Returns:
            是否全部通过
        """
        console.print()
        console.print(Panel.fit(
            "[bold blue]🔍 项目健康检查[/bold blue]\n\n"
            f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            border_style="blue"
        ))

        # 执行所有检查
        self.check_dependencies()
        self.check_config_files()
        self.check_auth_status()
        self.check_disk_space()
        self.check_database()
        self.check_logs()
        self.check_git_status()

        # 汇总结果
        console.print()
        console.print(Panel(
            self._generate_summary(),
            border_style="green" if self._all_passed() else "yellow",
            title="📊 检查结果"
        ))
        console.print()

        return self._all_passed()

    def _generate_summary(self) -> str:
        """生成总结"""
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c["status"])
        failed = total - passed

        lines = []
        lines.append(f"[bold]总检查项: {total}[/bold]\n")
        lines.append(f"  [green]✅ 通过: {passed}[/green]")
        if failed > 0:
            lines.append(f"  [red]❌ 失败: {failed}[/red]\n")
            lines.append("[bold]失败详情:[/bold]\n")
            for check in self.checks:
                if not check["status"]:
                    lines.append(f"  • [red]{check['name']}[/red]: {check['message']}")
        else:
            lines.append("\n[green]🎉 所有检查通过！项目状态健康！[/green]")

        return "\n".join(lines)

    def _all_passed(self) -> bool:
        """是否全部通过"""
        return all(c["status"] for c in self.checks)


def main():
    """运行健康检查"""
    checker = HealthChecker()
    all_ok = checker.run_all_checks()

    if not all_ok:
        console.print("\n[yellow]💡 建议运行修复:[/yellow]")
        console.print("  python -m src.media_tools.config_manager --fix\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
