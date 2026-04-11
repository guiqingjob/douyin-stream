#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据备份与恢复工具

功能：
- 备份下载的视频
- 备份转写的文稿
- 备份数据库
- 一键恢复
- 定时自动备份
"""

import shutil
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

console = Console()


class BackupManager:
    """数据备份管理器"""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root
        self.backup_dir = project_root / "backups" / "data"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        backup_name: str = "",
        include_videos: bool = True,
        include_transcripts: bool = True,
        include_database: bool = True,
        include_config: bool = True,
    ) -> Path:
        """创建数据备份

        Args:
            backup_name: 备份名称，默认使用时间戳
            include_videos: 是否包含视频
            include_transcripts: 是否包含文稿
            include_database: 是否包含数据库
            include_config: 是否包含配置

        Returns:
            备份目录路径
        """
        if not backup_name:
            backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[bold]📦 开始创建备份: {backup_name}[/bold]\n")

        total_files = 0
        total_size = 0

        # 备份视频文件
        if include_videos:
            videos_dir = self.project_root / "downloads"
            if videos_dir.exists():
                dest = backup_path / "downloads"
                count, size = self._copy_directory(videos_dir, dest)
                total_files += count
                total_size += size
                console.print(f"[green]✓[/green] 备份视频: {count} 个文件")

        # 备份文稿
        if include_transcripts:
            transcripts_dir = self.project_root / "transcripts"
            if transcripts_dir.exists():
                dest = backup_path / "transcripts"
                count, size = self._copy_directory(transcripts_dir, dest)
                total_files += count
                total_size += size
                console.print(f"[green]✓[/green] 备份文稿: {count} 个文件")

        # 备份数据库
        if include_database:
            db_file = self.project_root / "douyin_users.db"
            if db_file.exists():
                dest = backup_path / "douyin_users.db"
                shutil.copy2(db_file, dest)
                size = dest.stat().st_size
                total_files += 1
                total_size += size
                console.print(f"[green]✓[/green] 备份数据库")

        # 备份配置
        if include_config:
            config_dir = self.project_root / "config"
            if config_dir.exists():
                dest = backup_path / "config"
                count, size = self._copy_directory(config_dir, dest)
                total_files += count
                total_size += size
                console.print(f"[green]✓[/green] 备份配置: {count} 个文件")

        # 创建备份元数据
        metadata = {
            "name": backup_name,
            "created_at": datetime.now().isoformat(),
            "total_files": total_files,
            "total_size": total_size,
            "total_size_human": self._format_size(total_size),
            "includes": {
                "videos": include_videos,
                "transcripts": include_transcripts,
                "database": include_database,
                "config": include_config,
            }
        }

        metadata_file = backup_path / "backup.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        console.print(f"\n[bold green]✅ 备份完成！[/bold green]")
        console.print(f"  文件数: {total_files}")
        console.print(f"  总大小: {self._format_size(total_size)}")
        console.print(f"  位置: {backup_path}\n")

        return backup_path

    def restore_backup(
        self,
        backup_path: Path,
        restore_videos: bool = True,
        restore_transcripts: bool = True,
        restore_database: bool = True,
        restore_config: bool = True,
    ):
        """从备份恢复数据

        Args:
            backup_path: 备份目录路径
            restore_videos: 是否恢复视频
            restore_transcripts: 是否恢复文稿
            restore_database: 是否恢复数据库
            restore_config: 是否恢复配置
        """
        if not backup_path.exists():
            console.print(f"[red]❌ 备份不存在: {backup_path}[/red]\n")
            return

        # 读取元数据
        metadata_file = backup_path / "backup.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            console.print(f"[bold]📦 恢复备份: {metadata['name']}[/bold]\n")
        else:
            console.print(f"[bold]📦 恢复备份: {backup_path.name}[/bold]\n")

        # 恢复视频
        if restore_videos:
            src = backup_path / "downloads"
            if src.exists():
                dest = self.project_root / "downloads"
                self._copy_directory(src, dest, overwrite=False)
                console.print(f"[green]✓[/green] 恢复视频")

        # 恢复文稿
        if restore_transcripts:
            src = backup_path / "transcripts"
            if src.exists():
                dest = self.project_root / "transcripts"
                self._copy_directory(src, dest, overwrite=False)
                console.print(f"[green]✓[/green] 恢复文稿")

        # 恢复数据库
        if restore_database:
            src = backup_path / "douyin_users.db"
            if src.exists():
                dest = self.project_root / "douyin_users.db"
                shutil.copy2(src, dest)
                console.print(f"[green]✓[/green] 恢复数据库")

        # 恢复配置
        if restore_config:
            src = backup_path / "config"
            if src.exists():
                dest = self.project_root / "config"
                self._copy_directory(src, dest, overwrite=True)
                console.print(f"[green]✓[/green] 恢复配置")

        console.print(f"\n[bold green]✅ 数据恢复完成！[/bold green]\n")

    def list_backups(self):
        """列出所有备份"""
        if not self.backup_dir.exists():
            console.print("[yellow]⚠️  暂无备份[/yellow]\n")
            return

        backups = sorted(self.backup_dir.iterdir(), reverse=True)
        backups = [b for b in backups if b.is_dir()]

        if not backups:
            console.print("[yellow]⚠️  暂无备份[/yellow]\n")
            return

        console.print("\n[bold]💾 数据备份列表:[/bold]\n")

        table = Table(show_header=True, box=None)
        table.add_column("备份名称", style="cyan")
        table.add_column("创建时间", style="dim")
        table.add_column("文件数", justify="right")
        table.add_column("大小", justify="right")

        for backup in backups:
            metadata_file = backup / "backup.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                table.add_row(
                    metadata["name"],
                    datetime.fromisoformat(metadata["created_at"]).strftime("%Y-%m-%d %H:%M:%S"),
                    str(metadata["total_files"]),
                    metadata["total_size_human"],
                )
            else:
                table.add_row(
                    backup.name,
                    datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "-",
                    "-",
                )

        console.print(table)
        console.print()

    def delete_backup(self, backup_path: Path):
        """删除指定备份"""
        if backup_path.exists():
            shutil.rmtree(backup_path)
            console.print(f"[green]✓[/green] 已删除备份: {backup_path.name}\n")
        else:
            console.print(f"[red]❌ 备份不存在: {backup_path}[/red]\n")

    def _copy_directory(
        self,
        src: Path,
        dest: Path,
        overwrite: bool = True,
    ) -> tuple[int, int]:
        """复制目录

        Returns:
            (文件数, 总大小)
        """
        if not src.exists():
            return 0, 0

        count = 0
        total_size = 0

        for item in src.rglob("*"):
            if item.is_file():
                relative = item.relative_to(src)
                target = dest / relative
                target.parent.mkdir(parents=True, exist_ok=True)

                if not target.exists() or overwrite:
                    shutil.copy2(item, target)
                    count += 1
                    total_size += target.stat().st_size

        return count, total_size

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / 1024**2:.1f} MB"
        else:
            return f"{size_bytes / 1024**3:.2f} GB"


def interactive_backup_menu():
    """交互式备份菜单"""
    manager = BackupManager()

    while True:
        console.print("\n[bold]💾 数据备份与恢复[/bold]\n")
        console.print("  1. 创建完整备份")
        console.print("  2. 查看备份列表")
        console.print("  3. 恢复数据")
        console.print("  4. 删除备份")
        console.print("  0. 返回")
        print()

        try:
            choice = input("请选择操作 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0":
            return
        elif choice == "1":
            manager.create_backup()
            input("\n按回车键继续...")
        elif choice == "2":
            manager.list_backups()
            input("\n按回车键继续...")
        elif choice == "3":
            manager.list_backups()
            try:
                name = input("请输入备份名称: ").strip()
                if name:
                    backup_path = manager.backup_dir / name
                    manager.restore_backup(backup_path)
            except (EOFError, KeyboardInterrupt):
                pass
            input("\n按回车键继续...")
        elif choice == "4":
            manager.list_backups()
            try:
                name = input("请输入要删除的备份名称: ").strip()
                if name:
                    backup_path = manager.backup_dir / name
                    confirm = input(f"确认删除 {name}？(y/N): ").strip().lower()
                    if confirm == "y":
                        manager.delete_backup(backup_path)
            except (EOFError, KeyboardInterrupt):
                pass
            input("\n按回车键继续...")


def main():
    """独立运行备份工具"""
    import argparse

    parser = argparse.ArgumentParser(description="数据备份与恢复")
    parser.add_argument("--backup", action="store_true", help="创建备份")
    parser.add_argument("--restore", type=str, help="恢复指定备份")
    parser.add_argument("--list", action="store_true", help="列出备份")
    parser.add_argument("--interactive", action="store_true", help="交互模式")

    args = parser.parse_args()

    manager = BackupManager()

    if args.backup:
        manager.create_backup()
    elif args.restore:
        backup_path = manager.backup_dir / args.restore
        manager.restore_backup(backup_path)
    elif args.list:
        manager.list_backups()
    elif args.interactive:
        interactive_backup_menu()
    else:
        manager.list_backups()


if __name__ == "__main__":
    main()
