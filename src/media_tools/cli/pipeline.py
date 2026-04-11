"""Pipeline CLI 子命令"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from .orchestrator import (
    run_pipeline_single,
    run_pipeline_batch,
    print_pipeline_summary,
    PipelineConfig,
)
from .config import load_pipeline_config

console = Console()


def cmd_pipeline_run(
    video_path: str,
    output_dir: Optional[str] = None,
    export_format: Optional[str] = None,
    account_id: Optional[str] = None,
    remove_video: bool = False,
) -> None:
    """执行单个视频转写 Pipeline"""
    video = Path(video_path).resolve()
    
    if not video.exists():
        console.print(f"[red]❌ 视频文件不存在: {video}[/red]")
        return
    
    config = load_pipeline_config()
    if output_dir:
        config = PipelineConfig(
            export_format=export_format or config.export_format,
            output_dir=output_dir,
            export_format=config.export_format,
            delete_after_export=config.delete_after_export,
            account_id=account_id or config.account_id,
            remove_video=remove_video,
            keep_original=config.keep_original,
            concurrency=config.concurrency,
        )
    
    console.print(Panel(
        f"[bold]Pipeline 启动[/bold]\n\n"
        f"视频: {video}\n"
        f"输出: {config.output_dir}\n"
        f"格式: {config.export_format.upper()}",
        title="🚀 Media Tools Pipeline",
        border_style="blue"
    ))
    
    result = run_pipeline_single(video, config)
    
    if result.success:
        console.print(f"\n[green bold]✅ 转写成功![/green bold]")
        console.print(f"文稿: {result.transcript_path}")
    else:
        console.print(f"\n[red bold]❌ 转写失败[/red bold]")
        console.print(f"错误: {result.error}")


def cmd_pipeline_batch(
    video_dir: str,
    output_dir: Optional[str] = None,
    export_format: Optional[str] = None,
    concurrency: int = 1,
    pattern: str = "*.mp4",
) -> None:
    """批量转写目录下所有视频"""
    video_path = Path(video_dir).resolve()
    
    if not video_path.is_dir():
        console.print(f"[red]❌ 目录不存在: {video_path}[/red]")
        return
    
    # 查找所有视频文件
    video_files = list(video_path.glob(pattern))
    if not video_files:
        console.print(f"[yellow]⚠️  未找到匹配 '{pattern}' 的视频文件[/yellow]")
        return
    
    config = PipelineConfig(
        export_format=export_format or load_pipeline_config().export_format,
        output_dir=output_dir or load_pipeline_config().output_dir,
        delete_after_export=load_pipeline_config().delete_after_export,
        account_id=load_pipeline_config().account_id,
        remove_video=False,
        keep_original=load_pipeline_config().keep_original,
        concurrency=concurrency,
    )
    
    console.print(Panel(
        f"[bold]批量 Pipeline 启动[/bold]\n\n"
        f"目录: {video_path}\n"
        f"视频数: {len(video_files)}\n"
        f"并发: {config.concurrency}\n"
        f"输出: {config.output_dir}\n"
        f"格式: {config.export_format.upper()}",
        title="🚀 Media Tools Pipeline",
        border_style="blue"
    ))
    
    results = run_pipeline_batch(video_files, config)
    print_pipeline_summary(results)
