#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量操作汇总报告 - 生成详细的执行报告

功能：
- 汇总统计（成功/失败/跳过/耗时）
- 错误分类统计
- 每个任务的详细信息
- 导出为JSON或文本报告
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


class BatchReport:
    """批量操作报告"""

    def __init__(
        self,
        operation_name: str,
        start_time: Optional[datetime] = None,
    ):
        self.operation_name = operation_name
        self.start_time = start_time or datetime.now()
        self.end_time: Optional[datetime] = None
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0

        # 详细信息
        self.items = []  # [{name, status, duration, error, details}]
        self.error_types = {}  # {error_type: count}

    def add_item(
        self,
        name: str,
        status: str,  # success/failed/skipped
        duration: float = 0,
        error: str = "",
        details: str = "",
    ):
        """添加任务结果"""
        self.total += 1

        if status == "success":
            self.success += 1
        elif status == "failed":
            self.failed += 1
            # 统计错误类型
            error_type = self._classify_error(error)
            self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        elif status == "skipped":
            self.skipped += 1

        self.items.append({
            "name": name,
            "status": status,
            "duration": round(duration, 2),
            "error": error,
            "details": details,
        })

    def finish(self):
        """完成报告"""
        self.end_time = datetime.now()

    @property
    def duration(self) -> float:
        """总耗时（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total == 0:
            return 0
        return (self.success / self.total) * 100

    def _classify_error(self, error: str) -> str:
        """分类错误类型"""
        error_lower = error.lower()

        if any(kw in error_lower for kw in ["network", "timeout", "connection"]):
            return "网络错误"
        elif any(kw in error_lower for kw in ["auth", "login", "cookie", "token"]):
            return "认证错误"
        elif any(kw in error_lower for kw in ["quota", "limit", "exceeded"]):
            return "配额错误"
        elif any(kw in error_lower for kw in ["file", "not found", "path"]):
            return "文件错误"
        elif any(kw in error_lower for kw in ["config", "env"]):
            return "配置错误"
        else:
            return "其他错误"

    def display_summary(self):
        """显示摘要"""
        console.print()

        # 主统计
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("指标", style="cyan", width=15)
        summary_table.add_column("数值", style="green")

        summary_table.add_row("操作名称", self.operation_name)
        summary_table.add_row("总任务数", str(self.total))
        summary_table.add_row("成功", f"[green]{self.success}[/green]")
        summary_table.add_row("失败", f"[red]{self.failed}[/red]")
        summary_table.add_row("跳过", f"[yellow]{self.skipped}[/yellow]")
        summary_table.add_row("成功率", f"{self.success_rate:.1f}%")
        summary_table.add_row("总耗时", f"{self.duration:.1f}s")

        if self.total > 0:
            avg = self.duration / self.total
            summary_table.add_row("平均耗时", f"{avg:.1f}s/个")

        console.print(Panel(summary_table, border_style="blue", title="📊 批量操作摘要"))

    def display_error_summary(self):
        """显示错误类型统计"""
        if not self.error_types:
            return

        console.print("\n[bold red]❌ 错误类型分布:[/bold red]\n")

        error_table = Table(show_header=True, box=None)
        error_table.add_column("错误类型", style="red")
        error_table.add_column("数量", justify="right")
        error_table.add_column("占比", justify="right")

        total_errors = sum(self.error_types.values())
        for error_type, count in sorted(self.error_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_errors * 100) if total_errors > 0 else 0
            error_table.add_row(
                error_type,
                str(count),
                f"{percentage:.1f}%"
            )

        console.print(error_table)

    def display_failed_items(self):
        """显示失败任务详情"""
        failed = [item for item in self.items if item["status"] == "failed"]
        if not failed:
            return

        console.print("\n[bold red]❌ 失败任务详情:[/bold red]\n")

        for item in failed:
            console.print(f"  [red]•[/red] [bold]{item['name']}[/bold]")
            console.print(f"    错误: [dim]{item['error'][:100]}[/dim]")
            console.print()

    def display_full_report(self):
        """显示完整报告"""
        self.display_summary()
        self.display_error_summary()
        self.display_failed_items()

        console.print()

    def export_json(self, path: Path):
        """导出为JSON"""
        report_data = {
            "operation": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "summary": {
                "total": self.total,
                "success": self.success,
                "failed": self.failed,
                "skipped": self.skipped,
                "success_rate": self.success_rate,
            },
            "error_types": self.error_types,
            "items": self.items,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        console.print(f"[green]✓[/green] 报告已导出: [blue]{path}[/blue]")

    def export_text(self, path: Path):
        """导出为文本报告"""
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"📊 批量操作报告: {self.operation_name}")
        lines.append(f"{'='*60}")
        lines.append(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else '进行中'}")
        lines.append(f"总耗时: {self.duration:.1f}s")
        lines.append(f"")
        lines.append(f"统计:")
        lines.append(f"  总任务数: {self.total}")
        lines.append(f"  成功: {self.success}")
        lines.append(f"  失败: {self.failed}")
        lines.append(f"  跳过: {self.skipped}")
        lines.append(f"  成功率: {self.success_rate:.1f}%")
        lines.append(f"")

        if self.error_types:
            lines.append(f"错误类型分布:")
            for error_type, count in self.error_types.items():
                lines.append(f"  {error_type}: {count}")
            lines.append(f"")

        lines.append(f"任务详情:")
        for i, item in enumerate(self.items, 1):
            status_icon = "✅" if item["status"] == "success" else "❌" if item["status"] == "failed" else "⏭️"
            lines.append(f"  {i}. {status_icon} {item['name']} ({item['duration']:.1f}s)")
            if item["error"]:
                lines.append(f"     错误: {item['error'][:80]}")
        lines.append(f"")
        lines.append(f"{'='*60}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")

        console.print(f"[green]✓[/green] 报告已导出: [blue]{path}[/blue]")


def create_report(operation_name: str) -> BatchReport:
    """创建报告的便捷函数"""
    return BatchReport(operation_name)


def main():
    """测试报告功能"""
    import time

    print("📊 批量操作报告演示\n")

    # 创建模拟报告
    report = BatchReport("批量转写测试")

    # 添加模拟数据
    for i in range(1, 6):
        time.sleep(0.2)
        if i % 4 == 0:
            report.add_item(
                f"video_{i}.mp4",
                "failed",
                duration=1.5,
                error="Network timeout"
            )
        else:
            report.add_item(
                f"video_{i}.mp4",
                "success",
                duration=2.0,
                details="transcripts/video_{i}.md"
            )

    report.finish()

    # 显示报告
    report.display_full_report()

    # 导出报告
    report.export_json(Path("test_report.json"))
    report.export_text(Path("test_report.txt"))


if __name__ == "__main__":
    main()
