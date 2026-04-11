#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理中心 - 整合所有配置系统

功能：
- 统一管理所有配置文件
- 提供配置验证
- 配置导入/导出
- 配置备份
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class ConfigManager:
    """统一配置管理器"""

    def __init__(self):
        self.project_root = Path(".")
        self.config_dir = self.project_root / "config"
        self.backup_dir = self.config_dir / "backups"

        # 配置文件列表
        self.config_files = {
            "抖音配置": self.config_dir / "config.yaml",
            "关注列表": self.config_dir / "following.json",
            "转写环境变量": self.config_dir / "transcribe" / ".env",
            "转写账号配置": self.config_dir / "transcribe" / "accounts.json",
            "激活预设": self.config_dir / "active_preset.txt",
        }

    def validate_all(self) -> dict:
        """验证所有配置文件

        Returns:
            {file: {valid: bool, error: str}}
        """
        results = {}

        for name, path in self.config_files.items():
            if not path.exists():
                results[name] = {
                    "valid": False,
                    "error": "文件不存在",
                    "path": str(path),
                }
                continue

            # 验证文件内容
            try:
                if path.suffix == ".yaml":
                    with open(path, "r", encoding="utf-8") as f:
                        yaml.safe_load(f)
                    results[name] = {"valid": True, "path": str(path)}

                elif path.suffix == ".json":
                    with open(path, "r", encoding="utf-8") as f:
                        json.load(f)
                    results[name] = {"valid": True, "path": str(path)}

                elif path.suffix == ".txt":
                    content = path.read_text(encoding="utf-8").strip()
                    results[name] = {
                        "valid": len(content) > 0,
                        "path": str(path),
                        "error": "文件为空" if not content else None,
                    }

                elif path.name == ".env":
                    # .env文件格式检查
                    content = path.read_text(encoding="utf-8")
                    results[name] = {"valid": True, "path": str(path)}

            except Exception as e:
                results[name] = {
                    "valid": False,
                    "error": str(e),
                    "path": str(path),
                }

        return results

    def display_config_status(self):
        """显示配置状态"""
        console.print("\n[bold]📋 配置文件状态:[/bold]\n")

        table = Table(show_header=True, box=None)
        table.add_column("配置文件", style="cyan", width=20)
        table.add_column("路径", style="dim", width=35)
        table.add_column("状态", width=10)
        table.add_column("说明", width=30)

        validation = self.validate_all()

        for name, result in validation.items():
            path = result["path"]
            valid = result["valid"]
            status = "[green]✓[/green]" if valid else "[red]✗[/red]"

            # 说明
            if not valid:
                desc = f"[red]{result.get('error', '未知错误')}[/red]"
            else:
                desc = "[green]正常[/green]"

            table.add_row(name, path, status, desc)

        console.print(table)
        console.print()

    def backup_configs(self, backup_name: str = "") -> Path:
        """备份所有配置文件

        Args:
            backup_name: 备份名称，默认使用时间戳

        Returns:
            备份目录路径
        """
        if not backup_name:
            backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        backed_up = 0
        for name, config_path in self.config_files.items():
            if config_path.exists():
                dest = backup_path / config_path.name
                shutil.copy2(config_path, dest)
                backed_up += 1
                console.print(f"[green]✓[/green] 备份: {config_path}")

        console.print(f"\n[green]✅ 备份完成！共 {backed_up} 个文件 → {backup_path}[/green]\n")
        return backup_path

    def restore_configs(self, backup_path: Path):
        """从备份恢复配置

        Args:
            backup_path: 备份目录路径
        """
        if not backup_path.exists():
            console.print(f"[red]❌ 备份不存在: {backup_path}[/red]\n")
            return

        restored = 0
        for backup_file in backup_path.iterdir():
            if backup_file.is_file():
                # 找到原文件路径
                original_path = self.config_dir / backup_file.name

                # 如果是子目录的文件
                if not original_path.exists():
                    # 尝试在transcribe子目录
                    original_path = self.config_dir / "transcribe" / backup_file.name

                if original_path.parent.exists():
                    shutil.copy2(backup_file, original_path)
                    restored += 1
                    console.print(f"[green]✓[/green] 恢复: {original_path}")

        console.print(f"\n[green]✅ 恢复完成！共 {restored} 个文件[/green]\n")

    def export_configs(self, output_dir: Path):
        """导出所有配置到指定目录

        用于迁移或分享配置
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        exported = 0
        for name, config_path in self.config_files.items():
            if config_path.exists():
                # 保持目录结构
                relative_path = config_path.relative_to(self.config_dir)
                dest = output_dir / relative_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_path, dest)
                exported += 1
                console.print(f"[green]✓[/green] 导出: {dest}")

        console.print(f"\n[green]✅ 导出完成！共 {exported} 个文件 → {output_dir}[/green]\n")

    def import_configs(self, source_dir: Path):
        """从目录导入配置

        会覆盖现有配置，建议先备份
        """
        if not source_dir.exists():
            console.print(f"[red]❌ 源目录不存在: {source_dir}[/red]\n")
            return

        # 先备份
        console.print("[yellow]⚠️  导入前将自动备份现有配置...[/yellow]\n")
        self.backup_configs("before_import")

        imported = 0
        for config_file in source_dir.rglob("*"):
            if config_file.is_file():
                # 计算目标路径
                try:
                    relative_path = config_file.relative_to(source_dir)
                    dest = self.config_dir / relative_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(config_file, dest)
                    imported += 1
                    console.print(f"[green]✓[/green] 导入: {dest}")
                except Exception as e:
                    console.print(f"[red]✗[/red] 导入失败: {config_file} - {e}")

        console.print(f"\n[green]✅ 导入完成！共 {imported} 个文件[/green]\n")

    def list_backups(self):
        """列出所有备份"""
        if not self.backup_dir.exists():
            console.print("[yellow]⚠️  暂无备份[/yellow]\n")
            return

        backups = sorted(self.backup_dir.iterdir(), reverse=True)
        if not backups:
            console.print("[yellow]⚠️  暂无备份[/yellow]\n")
            return

        console.print("\n[bold]💾 备份列表:[/bold]\n")

        table = Table(show_header=True, box=None)
        table.add_column("备份名称", style="cyan")
        table.add_column("时间", style="dim")
        table.add_column("文件数", justify="right")
        table.add_column("大小", justify="right")

        for backup in backups:
            if backup.is_dir():
                file_count = len(list(backup.rglob("*")))
                size = sum(f.stat().st_size for f in backup.rglob("*") if f.is_file())
                size_str = f"{size / 1024:.1f} KB" if size < 1024**2 else f"{size / 1024**2:.1f} MB"

                table.add_row(
                    backup.name,
                    datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    str(file_count),
                    size_str,
                )

        console.print(table)
        console.print()

    def fix_common_issues(self):
        """修复常见配置问题"""
        console.print("\n[bold]🔧 正在修复常见配置问题...[/bold]\n")

        fixed = 0

        # 1. 创建缺失的配置目录
        for path in self.config_files.values():
            if path.parent != self.config_dir and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓[/green] 创建目录: {path.parent}")
                fixed += 1

        # 2. 从模板创建缺失的配置
        templates = {
            "config.yaml": "config/config.yaml.example",
            "following.json": "config/following.json.example",
            "transcribe/.env": "config/transcribe/.env.example",
            "transcribe/accounts.json": "config/transcribe/accounts.example.json",
        }

        for target, template in templates.items():
            target_path = self.project_root / target
            template_path = self.project_root / template

            if not target_path.exists() and template_path.exists():
                shutil.copy2(template_path, target_path)
                console.print(f"[green]✓[/green] 从模板创建: {target_path}")
                fixed += 1

        # 3. 修复following.json格式
        following_file = self.config_dir / "following.json"
        if following_file.exists():
            try:
                with open(following_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "users" not in data:
                    data = {"users": data if isinstance(data, list) else []}
                    with open(following_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    console.print(f"[green]✓[/green] 修复 following.json 格式")
                    fixed += 1
            except Exception:
                pass

        if fixed > 0:
            console.print(f"\n[green]✅ 修复完成！共修复 {fixed} 个问题[/green]\n")
        else:
            console.print("[green]✅ 未发现常见配置问题[/green]\n")


def interactive_config_menu():
    """交互式配置菜单"""
    import questionary

    manager = ConfigManager()

    while True:
        console.print("\n[bold]⚙️  配置管理中心[/bold]\n")
        manager.display_config_status()

        choice = questionary.select(
            "选择操作:",
            choices=[
                "🔍 验证所有配置",
                "💾 备份配置",
                "♻️  恢复配置",
                "📤 导出配置",
                "📥 导入配置",
                "📋 查看备份列表",
                "🔧 修复常见问题",
                "⏭️  返回",
            ]
        ).ask()

        if choice == "🔍 验证所有配置":
            manager.display_config_status()
        elif choice == "💾 备份配置":
            manager.backup_configs()
        elif choice == "♻️  恢复配置":
            backups = list(manager.backup_dir.iterdir()) if manager.backup_dir.exists() else []
            if not backups:
                console.print("[yellow]⚠️  暂无备份[/yellow]\n")
                continue

            backup_choice = questionary.select(
                "选择要恢复的备份:",
                choices=[b.name for b in sorted(backups, reverse=True)]
            ).ask()

            if backup_choice:
                backup_path = manager.backup_dir / backup_choice
                manager.restore_configs(backup_path)

        elif choice == "📤 导出配置":
            try:
                output = input("请输入导出目录 (默认: ./config_export): ").strip()
                if not output:
                    output = "./config_export"
                manager.export_configs(Path(output))
            except (EOFError, KeyboardInterrupt):
                pass

        elif choice == "📥 导入配置":
            try:
                source = input("请输入导入目录: ").strip()
                if source:
                    manager.import_configs(Path(source))
            except (EOFError, KeyboardInterrupt):
                pass

        elif choice == "📋 查看备份列表":
            manager.list_backups()

        elif choice == "🔧 修复常见问题":
            manager.fix_common_issues()

        elif choice == "⏭️  返回":
            return

        input("\n按回车键继续...")


def main():
    """独立运行配置管理"""
    import argparse

    parser = argparse.ArgumentParser(description="配置管理中心")
    parser.add_argument("--status", action="store_true", help="显示配置状态")
    parser.add_argument("--backup", action="store_true", help="备份配置")
    parser.add_argument("--fix", action="store_true", help="修复常见问题")
    parser.add_argument("--interactive", action="store_true", help="交互式菜单")

    args = parser.parse_args()

    manager = ConfigManager()

    if args.status:
        manager.display_config_status()
    elif args.backup:
        manager.backup_configs()
    elif args.fix:
        manager.fix_common_issues()
    elif args.interactive:
        interactive_config_menu()
    else:
        # 默认显示状态
        manager.display_config_status()


if __name__ == "__main__":
    main()
