#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创作数据统计面板 - 显示使用统计和数据分析

统计内容：
- 下载视频数量
- 转写文稿数量
- 总转写字数
- 估算节省时间
- 热门博主排行
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class StatsCollector:
    """统计收集器"""

    def __init__(self):
        self.stats_file = Path(".usage_stats.json")
        self.stats = self._load_stats()

    def _load_stats(self) -> dict:
        """加载统计数据"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "total_downloads": 0,
            "total_transcribes": 0,
            "total_words": 0,
            "creators": {},  # {nickname: {"videos": 0, "words": 0}}
            "first_use": datetime.now().isoformat(),
            "last_use": datetime.now().isoformat(),
        }

    def save_stats(self):
        """保存统计数据"""
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def record_download(self, creator_name: str = "", video_count: int = 1):
        """记录下载"""
        self.stats["total_downloads"] += video_count
        self.stats["last_use"] = datetime.now().isoformat()

        if creator_name:
            if creator_name not in self.stats["creators"]:
                self.stats["creators"][creator_name] = {"videos": 0, "words": 0}
            self.stats["creators"][creator_name]["videos"] += video_count

        self.save_stats()

    def record_transcribe(self, creator_name: str = "", word_count: int = 0):
        """记录转写"""
        self.stats["total_transcribes"] += 1
        self.stats["total_words"] += word_count
        self.stats["last_use"] = datetime.now().isoformat()

        if creator_name:
            if creator_name not in self.stats["creators"]:
                self.stats["creators"][creator_name] = {"videos": 0, "words": 0}
            self.stats["creators"][creator_name]["words"] += word_count

        self.save_stats()

    def get_summary(self) -> dict:
        """获取统计摘要"""
        first_use = datetime.fromisoformat(self.stats["first_use"])
        days_active = (datetime.now() - first_use).days + 1

        # 估算节省时间：每个视频平均节省30分钟（下载+手动整理）
        # 每次转写平均节省20分钟（手动听写）
        estimated_time_saved = (
            self.stats["total_downloads"] * 30 +
            self.stats["total_transcribes"] * 20
        ) / 60  # 转换为小时

        return {
            "days_active": days_active,
            "total_downloads": self.stats["total_downloads"],
            "total_transcribes": self.stats["total_transcribes"],
            "total_words": self.stats["total_words"],
            "estimated_hours_saved": round(estimated_time_saved, 1),
            "total_creators": len(self.stats["creators"]),
        }

    def get_top_creators(self, limit: int = 5) -> list:
        """获取热门创作者排行"""
        creators = self.stats["creators"]
        if not creators:
            return []

        # 按视频数排序
        sorted_creators = sorted(
            creators.items(),
            key=lambda x: x[1]["videos"],
            reverse=True
        )[:limit]

        return [
            {"name": name, "videos": data["videos"], "words": data["words"]}
            for name, data in sorted_creators
        ]


def display_stats_panel():
    """显示统计面板"""
    collector = StatsCollector()
    summary = collector.get_summary()

    # 主统计面板
    stats_table = Table(title="📊 创作数据统计", show_header=False, box=None)
    stats_table.add_column("指标", style="cyan", width=20)
    stats_table.add_column("数值", style="green", justify="right")

    stats_table.add_row("📅 使用天数", f"{summary['days_active']} 天")
    stats_table.add_row("📥 下载视频", f"{summary['total_downloads']} 个")
    stats_table.add_row("📝 转写文稿", f"{summary['total_transcribes']} 篇")
    stats_table.add_row("📈 总转写字数", f"{summary['total_words']:,} 字")
    stats_table.add_row("⏱️  估算节省时间", f"{summary['estimated_hours_saved']} 小时")
    stats_table.add_row("👥 关注创作者", f"{summary['total_creators']} 位")

    console.print()
    console.print(Panel(stats_table, border_style="blue"))

    # 热门创作者
    top_creators = collector.get_top_creators()
    if top_creators:
        console.print()
        console.print("[bold]🏆 热门创作者 TOP 5[/bold]\n")

        creators_table = Table(box=None, show_header=True)
        creators_table.add_column("排名", style="yellow", width=6)
        creators_table.add_column("创作者", style="cyan", width=25)
        creators_table.add_column("视频数", style="green", justify="right")
        creators_table.add_column("转写字数", style="magenta", justify="right")

        for i, creator in enumerate(top_creators, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f" {i}."
            creators_table.add_row(
                f"{medal}",
                creator["name"],
                str(creator["videos"]),
                f"{creator['words']:,}" if creator["words"] > 0 else "-"
            )

        console.print(creators_table)

    console.print()


def auto_scan_and_update_stats():
    """自动扫描现有数据并更新统计"""
    from rich.progress import Progress

    console.print("[yellow]🔍 正在扫描现有数据...[/yellow]\n")

    collector = StatsCollector()
    updated = False

    # 扫描下载目录
    downloads_dir = Path("downloads")
    if downloads_dir.exists():
        video_files = list(downloads_dir.rglob("*.mp4"))
        if video_files:
            collector.stats["total_downloads"] = len(video_files)
            updated = True
            console.print(f"[green]✓[/green] 发现 {len(video_files)} 个已下载视频")

    # 扫描转写目录
    transcripts_dir = Path("transcripts")
    if transcripts_dir.exists():
        transcript_files = list(transcripts_dir.rglob("*.md")) + \
                          list(transcripts_dir.rglob("*.docx"))
        if transcript_files:
            collector.stats["total_transcribes"] = len(transcript_files)

            # 估算字数（读取MD文件）
            total_words = 0
            for md_file in transcript_files:
                if md_file.suffix == ".md":
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        # 简单估算：中文字符数
                        total_words += len([c for c in content if '\u4e00' <= c <= '\u9fff'])
                    except Exception:
                        pass

            collector.stats["total_words"] = total_words
            updated = True
            console.print(f"[green]✓[/green] 发现 {len(transcript_files)} 个转写文稿")

    if updated:
        collector.save_stats()
        console.print("\n[green]✅ 统计已更新！[/green]\n")
    else:
        console.print("\n[yellow]⚠️  未发现现有数据[/yellow]\n")


def main():
    """独立运行统计面板"""
    import argparse

    parser = argparse.ArgumentParser(description="创作数据统计面板")
    parser.add_argument("--scan", action="store_true",
                       help="扫描现有数据并更新统计")
    parser.add_argument("--reset", action="store_true",
                       help="重置统计数据")

    args = parser.parse_args()

    if args.scan:
        auto_scan_and_update_stats()
        display_stats_panel()
    elif args.reset:
        stats_file = Path(".usage_stats.json")
        if stats_file.exists():
            stats_file.unlink()
            console.print("[green]✅ 统计数据已重置[/green]")
    else:
        display_stats_panel()


if __name__ == "__main__":
    main()
