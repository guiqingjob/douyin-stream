#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务进度可视化面板 - 实时显示长时间任务进度

功能：
- 显示当前任务进度（百分比、已用时间、预估剩余时间）
- 显示每个子任务的状态（等待中/处理中/成功/失败）
- 支持暂停/取消操作
- 实时更新终端输出
"""

import time
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
)
from rich.layout import Layout
from rich.text import Text

console = Console()


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "⏳ 等待中"
    RUNNING = "🔄 处理中"
    SUCCESS = "✅ 成功"
    FAILED = "❌ 失败"
    SKIPPED = "⏭️  已跳过"
    CANCELLED = "🚫 已取消"


class TaskItem:
    """单个任务项"""
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.status = TaskStatus.PENDING
        self.error_message: Optional[str] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.details: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """任务耗时（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None

    def start(self):
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.start_time = time.time()

    def complete(self, details: str = ""):
        """完成任务"""
        self.status = TaskStatus.SUCCESS
        self.end_time = time.time()
        self.details = details

    def fail(self, error: str):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.end_time = time.time()
        self.error_message = error

    def skip(self, reason: str = ""):
        """跳过任务"""
        self.status = TaskStatus.SKIPPED
        self.details = reason


class TaskProgressPanel:
    """任务进度面板"""

    def __init__(
        self,
        total: int,
        title: str = "📦 任务进度",
        on_cancel: Optional[Callable] = None,
    ):
        self.total = total
        self.title = title
        self.tasks: list[TaskItem] = []
        self.current_index = 0
        self.start_time = time.time()
        self.on_cancel = on_cancel
        self.cancelled = False

        # Rich进度条
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
        )
        self.progress_task = None

    def add_task(self, task: TaskItem):
        """添加任务项"""
        self.tasks.append(task)

    def update(self):
        """更新面板显示"""
        if not self.tasks:
            return

        # 更新或创建进度任务
        if self.progress_task is None:
            self.progress_task = self.progress.add_task(
                self.title,
                total=self.total,
            )

        # 计算已完成数量
        completed = sum(1 for t in self.tasks if t.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED])
        self.progress.update(self.progress_task, completed=completed)

    def show_detail_table(self) -> Table:
        """显示任务详情表格"""
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("#", style="dim", width=4)
        table.add_column("状态", width=12)
        table.add_column("文件名", width=40)
        table.add_column("耗时", justify="right", width=10)
        table.add_column("详情", width=30)

        for i, task in enumerate(self.tasks, 1):
            # 状态
            status_style = "green" if task.status == TaskStatus.SUCCESS else \
                          "red" if task.status == TaskStatus.FAILED else \
                          "yellow" if task.status == TaskStatus.RUNNING else "dim"

            # 耗时
            duration_str = ""
            if task.duration:
                duration_str = f"{task.duration:.1f}s"

            # 详情
            detail = task.details or task.error_message or ""
            if len(detail) > 30:
                detail = detail[:27] + "..."

            table.add_row(
                str(i),
                f"[{status_style}]{task.status.value}[/{status_style}]",
                task.name[:40],
                duration_str,
                detail,
            )

        return table

    def get_summary(self) -> str:
        """获取任务摘要"""
        total = len(self.tasks)
        success = sum(1 for t in self.tasks if t.status == TaskStatus.SUCCESS)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in self.tasks if t.status == TaskStatus.SKIPPED)
        running = sum(1 for t in self.tasks if t.status == TaskStatus.RUNNING)
        pending = sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)

        elapsed = time.time() - self.start_time

        summary = []
        summary.append(f"[bold]任务摘要:[/bold]")
        summary.append(f"  总计: {total} | "
                      f"[green]成功: {success}[/green] | "
                      f"[red]失败: {failed}[/red] | "
                      f"[yellow]跳过: {skipped}[/yellow]")
        if running > 0:
            summary.append(f"  处理中: {running}")
        if pending > 0:
            summary.append(f"  等待中: {pending}")
        summary.append(f"  已用时间: {elapsed:.1f}s")

        # 预估剩余时间
        if success + failed > 0:
            avg_time = elapsed / (success + failed)
            remaining = avg_time * (pending + running)
            summary.append(f"  预估剩余: {remaining:.1f}s")

        return "\n".join(summary)

    def render(self) -> Panel:
        """渲染面板"""
        layout = Layout()

        # 统计摘要
        summary_text = self.get_summary()
        summary_panel = Panel(summary_text, border_style="cyan", title="📊 统计")

        # 任务详情
        detail_table = self.show_detail_table()

        layout.split_column(
            Layout(summary_panel, size=10),
            Layout(detail_table),
        )

        return Panel(layout, border_style="blue", title=self.title)


def create_progress_callback(
    panel: TaskProgressPanel,
    video_paths: list[Path],
) -> Callable:
    """创建进度回调函数

    Returns:
        callback(current, total, video_path, status)
    """
    # 预先创建所有任务项
    for path in video_paths:
        task = TaskItem(path.name, path)
        panel.add_task(task)

    def callback(current: int, total: int, video_path: Path, status: str):
        # 更新任务状态
        if current <= len(panel.tasks):
            task = panel.tasks[current - 1]

            if "成功" in status or "完成" in status:
                task.complete(details=status)
            elif "失败" in status or "错误" in status:
                task.fail(error=status)
            elif "跳过" in status:
                task.skip(reason=status)
            elif "处理" in status or "上传" in status:
                task.start()

        panel.update()

    return callback


def display_final_report(report_data: dict) -> Panel:
    """显示最终报告"""
    console.print()

    # 成功/失败统计
    total = report_data.get("total", 0)
    success = report_data.get("success", 0)
    failed = report_data.get("failed", 0)
    skipped = report_data.get("skipped", 0)
    elapsed = report_data.get("elapsed", 0)

    success_rate = (success / total * 100) if total > 0 else 0

    report = Panel(
        f"[bold]📊 执行报告[/bold]\n\n"
        f"  总计: {total} 个任务\n"
        f"  [green]✅ 成功: {success}[/green]\n"
        f"  [red]❌ 失败: {failed}[/red]\n"
        f"  [yellow]⏭️  跳过: {skipped}[/yellow]\n"
        f"  成功率: {success_rate:.1f}%\n"
        f"  总耗时: {elapsed:.1f}s\n"
        f"  平均耗时: {elapsed/total:.1f}s/个\n",
        border_style="green" if success_rate > 80 else "yellow" if success_rate > 50 else "red",
    )

    console.print(report)

    # 失败详情
    if failed > 0 and "failures" in report_data:
        console.print("\n[bold red]❌ 失败详情:[/bold red]\n")
        for failure in report_data["failures"]:
            console.print(f"  • [red]{failure['name']}[/red]: {failure['error']}")

    console.print()


def main():
    """测试进度面板"""
    import random

    print("📦 任务进度面板演示\n")

    # 创建模拟任务
    video_paths = [Path(f"video_{i}.mp4") for i in range(1, 6)]
    panel = TaskProgressPanel(total=len(video_paths), title="🎬 批量转写测试")

    # 创建回调
    callback = create_progress_callback(panel, video_paths)

    # 模拟任务执行
    with Live(panel.render(), refresh_per_second=2) as live:
        for i, path in enumerate(video_paths, 1):
            # 开始
            callback(i, len(video_paths), path, "处理中...")
            time.sleep(random.uniform(0.5, 1.5))

            # 随机成功/失败
            if random.random() > 0.2:
                callback(i, len(video_paths), path, "转写成功")
            else:
                callback(i, len(video_paths), path, "失败: 网络错误")

            live.update(panel.render())
            time.sleep(0.3)

    # 显示报告
    report_data = {
        "total": len(video_paths),
        "success": sum(1 for t in panel.tasks if t.status == TaskStatus.SUCCESS),
        "failed": sum(1 for t in panel.tasks if t.status == TaskStatus.FAILED),
        "skipped": sum(1 for t in panel.tasks if t.status == TaskStatus.SKIPPED),
        "elapsed": time.time() - panel.start_time,
    }

    display_final_report(report_data)


if __name__ == "__main__":
    main()
