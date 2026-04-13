
from media_tools.logger import get_logger
logger = get_logger(__name__)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具 - 追踪和分析程序性能

功能：
- 函数执行时间追踪
- 内存使用监控
- 慢操作检测
- 性能报告生成
"""

import time
import functools
from pathlib import Path
from typing import Optional, Callable
from contextlib import contextmanager

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class PerformanceTracker:
    """性能追踪器"""

    def __init__(self):
        self.operations = []  # [{name, duration, timestamp}]
        self.start_times = {}  # {operation_name: start_time}

    @contextmanager
    def track(self, operation_name: str):
        """追踪操作耗时

        Usage:
            tracker = PerformanceTracker()
            with tracker.track("下载视频"):
                # 执行下载
                pass
        """
        start_time = time.time()
        self.start_times[operation_name] = start_time

        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self.operations.append({
                "name": operation_name,
                "duration": duration,
                "timestamp": time.time(),
            })

            # 移除慢操作警告（超过5秒）
            if duration > 5.0:
                console.print(f"\n[yellow]⚠️  慢操作警告: {operation_name} 耗时 {duration:.1f}s[/yellow]\n")

    def get_operation_duration(self, operation_name: str) -> Optional[float]:
        """获取操作耗时"""
        for op in self.operations:
            if op["name"] == operation_name:
                return op["duration"]
        return None

    def get_total_duration(self) -> float:
        """获取总耗时"""
        return sum(op["duration"] for op in self.operations)

    def get_slow_operations(self, threshold: float = 5.0) -> list:
        """获取慢操作列表"""
        return [op for op in self.operations if op["duration"] > threshold]

    def get_summary(self) -> dict:
        """获取性能摘要"""
        if not self.operations:
            return {
                "total_operations": 0,
                "total_duration": 0,
                "average_duration": 0,
                "slowest_operation": None,
                "fastest_operation": None,
            }

        durations = [op["duration"] for op in self.operations]
        slowest = max(self.operations, key=lambda x: x["duration"])
        fastest = min(self.operations, key=lambda x: x["duration"])

        return {
            "total_operations": len(self.operations),
            "total_duration": sum(durations),
            "average_duration": sum(durations) / len(durations),
            "slowest_operation": slowest,
            "fastest_operation": fastest,
        }

    def display_report(self):
        """显示性能报告"""
        if not self.operations:
            console.print("[yellow]⚠️  暂无性能数据[/yellow]\n")
            return

        summary = self.get_summary()

        console.print()
        console.print(Panel(
            f"[bold]📊 性能报告[/bold]\n\n"
            f"  总操作数: {summary['total_operations']}\n"
            f"  总耗时: {summary['total_duration']:.2f}s\n"
            f"  平均耗时: {summary['average_duration']:.2f}s\n"
            f"  最慢操作: {summary['slowest_operation']['name']} ({summary['slowest_operation']['duration']:.2f}s)\n"
            f"  最快操作: {summary['fastest_operation']['name']} ({summary['fastest_operation']['duration']:.2f}s)",
            border_style="cyan",
            title="性能统计"
        ))

        # 详细表格
        console.print("\n[bold]操作详情:[/bold]\n")

        table = Table(show_header=True, box=None)
        table.add_column("#", style="dim", width=4)
        table.add_column("操作名称", style="cyan")
        table.add_column("耗时", justify="right", style="green")
        table.add_column("占比", justify="right")

        total = summary["total_duration"]
        for i, op in enumerate(self.operations, 1):
            percentage = (op["duration"] / total * 100) if total > 0 else 0

            # 慢操作标红
            if op["duration"] > 5.0:
                style = "red"
            elif op["duration"] > 2.0:
                style = "yellow"
            else:
                style = "green"

            table.add_row(
                str(i),
                op["name"],
                f"[{style}]{op['duration']:.2f}s[/{style}]",
                f"{percentage:.1f}%"
            )

        console.print(table)
        console.print()


def track_performance(func: Callable) -> Callable:
    """装饰器：追踪函数执行时间

    Usage:
        @track_performance
        def my_function():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time

        if duration > 5.0:
            console.print(f"\n[yellow]⚠️  慢函数警告: {func.__name__} 耗时 {duration:.2f}s[/yellow]\n")

        return result
    return wrapper


# 全局性能追踪器
_global_tracker: Optional[PerformanceTracker] = None


def get_tracker() -> PerformanceTracker:
    """获取全局性能追踪器"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = PerformanceTracker()
    return _global_tracker


def track_operation(name: str):
    """装饰器：追踪操作（可自定义名称）

    Usage:
        @track_operation("下载视频")
        def download_video():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_tracker()
            with tracker.track(name or func.__name__):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def main():
    """测试性能监控"""
    import time

    logger.info("📊 性能监控工具演示\n")

    tracker = PerformanceTracker()

    # 模拟各种操作
    with tracker.track("初始化配置"):
        time.sleep(0.1)

    with tracker.track("下载视频"):
        time.sleep(1.5)

    with tracker.track("上传OSS"):
        time.sleep(2.3)

    with tracker.track("AI转写"):
        time.sleep(6.5)  # 慢操作

    with tracker.track("导出文稿"):
        time.sleep(0.3)

    # 显示报告
    tracker.display_report()

    # 测试装饰器
    logger.info("\n测试装饰器:\n")

    @track_performance
    def slow_function():
        time.sleep(1.2)
        return "done"

    result = slow_function()
    logger.info(f"函数执行结果: {result}")

    logger.info("\n✅ 性能监控测试完成！\n")


if __name__ == "__main__":
    main()
