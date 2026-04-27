"""Pipeline 任务辅助函数"""
from __future__ import annotations

import asyncio
import inspect
import logging
from pathlib import Path
from typing import Any

from media_tools.pipeline.media_extensions import MEDIA_EXTENSIONS

logger = logging.getLogger(__name__)

# 跟踪所有后台任务，防止 GC 导致静默失败
_background_tasks: set[asyncio.Task[Any]] = set()

MIN_VIDEO_BYTES = 10240  # 10KB


async def call_progress(update_progress_fn, progress: float, msg: str, stage: str = "") -> None:
    if not update_progress_fn:
        return
    try:
        if stage:
            try:
                result = update_progress_fn(progress, msg, stage)
            except TypeError:
                result = update_progress_fn(progress, msg)
        else:
            result = update_progress_fn(progress, msg)
        if inspect.isawaitable(result):
            await result
    except (TypeError, ValueError, RuntimeError) as e:
        logger.error(f"update_progress_fn 内部抛错: {e}")


def create_managed_task(coro) -> asyncio.Task[Any]:
    """创建受管理的后台任务，自动跟踪并在 done 时检查异常"""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)

    def _on_done(t: asyncio.Task[Any]) -> None:
        _background_tasks.discard(t)
        if t.cancelled() or not t.done():
            return
        exc = t.exception()
        if exc is not None:
            logger.error(f"Background task failed: {exc!r}")

    task.add_done_callback(_on_done)
    return task


def filter_supported_media_paths(file_paths: list[str]) -> list[Path]:
    valid_paths: list[Path] = []
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists() and path.suffix.lower() in MEDIA_EXTENSIONS and path.stat().st_size >= MIN_VIDEO_BYTES:
            valid_paths.append(path)
    return valid_paths
