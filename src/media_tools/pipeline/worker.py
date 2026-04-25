import asyncio
import inspect
import sqlite3
from pathlib import Path
from typing import Any
from media_tools.logger import get_logger
from media_tools.pipeline.media_extensions import MEDIA_EXTENSIONS
from media_tools.db.core import local_asset_id

logger = get_logger('pipeline')
# 跟踪所有后台任务，防止 GC 导致静默失败
_background_tasks: set[asyncio.Task[Any]] = set()


async def _call_progress(update_progress_fn, progress: float, msg: str) -> None:
    if not update_progress_fn:
        return
    try:
        result = update_progress_fn(progress, msg)
        if inspect.isawaitable(result):
            await result
    except (TypeError, ValueError, RuntimeError) as e:
        logger.error(f"update_progress_fn 内部抛错: {e}")


def _create_managed_task(coro) -> asyncio.Task[Any]:
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


MIN_VIDEO_BYTES = 10240  # 10KB，正常视频文件至少几百KB


def filter_supported_media_paths(file_paths: list[str]) -> list[Path]:
    valid_paths: list[Path] = []
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists() and path.suffix.lower() in MEDIA_EXTENSIONS and path.stat().st_size >= MIN_VIDEO_BYTES:
            valid_paths.append(path)
    return valid_paths


async def run_local_transcribe(file_paths: list[str], update_progress_fn=None, delete_after: bool = False):
    """转写本地视频文件（不经过下载步骤）"""
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    valid_paths = filter_supported_media_paths(file_paths)

    if not valid_paths:
        return {"success_count": 0, "failed_count": 0, "total": 0}

    config = load_pipeline_config()
    # 不设置 creator_folder_override，让它自动从视频路径提取创作者名称
    orchestrator = create_orchestrator(config)
    output_root = Path(config.output_dir).resolve()

    success_count = 0
    failed_count = 0
    total = len(valid_paths)

    await _call_progress(update_progress_fn, 0.0, f"准备转写 {total} 个文件（并发 {config.concurrency}）")
    try:
        report = await orchestrator.transcribe_batch(valid_paths, resume=True)
    except (OSError, asyncio.TimeoutError, RuntimeError) as exc:
        logger.error(f"批量本地转写失败: {exc}")
        failed_count = total
        return {"success_count": success_count, "failed_count": failed_count, "total": total}

    from media_tools.db.core import get_db_connection
    from media_tools.pipeline.preview import extract_transcript_preview, extract_transcript_text

    for item in report.results:
        video_path = Path(item["video_path"])
        if item.get("success"):
            success_count += 1
            try:
                transcript_path = item.get("transcript_path")
                transcript_name = ""
                preview = ""
                full_text = ""
                if transcript_path:
                    try:
                        transcript_name = str(Path(transcript_path).resolve().relative_to(output_root))
                    except ValueError:
                        # 路径不在 output_root 下，使用文件名
                        transcript_name = str(Path(transcript_path).name)
                    preview = extract_transcript_preview(transcript_path)
                    full_text = extract_transcript_text(transcript_path)
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        UPDATE media_assets
                        SET transcript_path = ?, transcript_status = 'completed', transcript_preview = ?, transcript_text = ?, update_time = CURRENT_TIMESTAMP
                        WHERE asset_id = ?
                        """,
                        (transcript_name, preview, full_text, local_asset_id(video_path)),
                    )
                    conn.commit()
                    # Keep FTS5 index in sync
                    try:
                        from media_tools.db.core import update_fts_for_asset
                        title_row = conn.execute(
                            "SELECT title FROM media_assets WHERE asset_id = ?",
                            (local_asset_id(video_path),),
                        ).fetchone()
                        update_fts_for_asset(
                            local_asset_id(video_path),
                            title_row["title"] if title_row else "",
                            full_text,
                        )
                    except sqlite3.Error:
                        pass
            except sqlite3.Error:
                pass
            if delete_after and video_path.exists():
                try:
                    video_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError as e:
                    logger.error(f"删除视频失败 (DB已更新): {video_path}, {e}")
        else:
            failed_count += 1

        completed = success_count + failed_count
        await _call_progress(
            update_progress_fn,
            completed / total,
            f"已处理 {completed}/{total}",
        )

    # 构建子任务列表
    subtasks = []
    for item in report.results:
        video_path = Path(item["video_path"])
        status = "completed" if item.get("success") else "failed"
        error = item.get("error") if not item.get("success") else None
        subtasks.append({
            "title": video_path.stem,
            "status": status,
            "error": error,
        })

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "total": total,
        "subtasks": subtasks,
    }


async def run_pipeline_for_user(url: str, max_counts: int, update_progress_fn, delete_after: bool = True, task_id: str | None = None):
    from media_tools.pipeline.download_router import download_by_url as download_router
    from media_tools.pipeline.download_router import resolve_platform
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    await _call_progress(update_progress_fn, 0.1, "正在下载视频...")

    # 1. Download - 使用 router（会自动选择 yt-dlp 或回退到 F2）
    platform = resolve_platform(url)

    try:
        if platform == "bilibili":
            # B站使用 yt-dlp
            from media_tools.bilibili.core.downloader import download_up_by_url as bilibili_download
            dl_result = await asyncio.wait_for(
                asyncio.to_thread(bilibili_download, url, max_counts, True, None, task_id),
                timeout=600,
            )
        else:
            # 抖音使用 download_router（会自动选择 yt-dlp 视频或回退到 F2 用户主页）
            # disable_auto_transcribe=True：pipeline 模式由 run_pipeline_for_user 自己控制转写
            dl_result = await asyncio.wait_for(
                asyncio.to_thread(download_router, url, max_counts, True, True, task_id),
                timeout=600,
            )
    except asyncio.TimeoutError:
        logger.error(f"下载超时 (task_id={task_id}): {url}")
        await _call_progress(update_progress_fn, 1.0, "下载超时，请检查网络或链接是否可用")
        return {"success_count": 0, "failed_count": 0, "error": "下载超时"}
    except asyncio.CancelledError:
        logger.info(f"下载任务被取消 (task_id={task_id})")
        raise

    # 检查是否被取消（下载完成后）
    if isinstance(dl_result, dict) and dl_result.get("cancelled"):
        await _call_progress(update_progress_fn, 1.0, "任务已取消")
        return {"success_count": 0, "failed_count": 0, "cancelled": True}

    new_files = dl_result.get('new_files', []) if isinstance(dl_result, dict) else []

    if not new_files:
        await _call_progress(update_progress_fn, 1.0, "没有下载到新视频")
        return {"success_count": 0, "failed_count": 0}

    await _call_progress(update_progress_fn, 0.4, f"下载完成，准备转写 {len(new_files)} 个视频...")

    # 2. Transcribe (并发批量转写)
    config = load_pipeline_config()
    state_file = Path(f".pipeline_state_{task_id or 'default'}.json")
    orchestrator = create_orchestrator(config, state_file=state_file)

    total = len(new_files)

    # 使用批量并发转写
    def _progress_callback(current: int, total: int, video_path: Path, status: str):
        progress = 0.4 + 0.6 * (current / total) if total > 0 else 0.4
        result = update_progress_fn(progress, status)
        if inspect.isawaitable(result):
            _create_managed_task(result)
        elif result is not None:
            logger.warning(f"update_progress_fn 返回非协程: {type(result)}")
        return None

    orchestrator.on_progress = _progress_callback

    # 转换为 Path 对象
    video_paths = [Path(f) for f in new_files]

    # 并发执行批量转写
    report = await orchestrator.transcribe_batch(video_paths, resume=False)

    success_count = report.success
    failed_count = report.failed
    successful_paths = {
        str(Path(item["video_path"]).resolve())
        for item in getattr(report, "results", [])
        if item.get("success") and item.get("video_path")
    }

    # 删除已转写的视频（如果配置了 delete_after）
    if delete_after:
        for path in video_paths:
            if str(path.resolve()) not in successful_paths:
                continue
            if path.exists():
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                except OSError as e:
                    logger.error(f"删除视频失败 (DB已更新): {path}, {e}")

    await _call_progress(update_progress_fn, 1.0, f"流水线完成: 成功 {success_count}, 失败 {failed_count}")

    # 构建子任务列表（O(N) Map 查找替代 O(N*M) 双重循环）
    subtasks = []
    total = len(new_files)
    result_by_path: dict[str, dict] = {}
    for r in report.results:
        vp = r.get("video_path", "")
        if vp:
            result_by_path[str(Path(vp).resolve())] = r

    for video_path in video_paths:
        result_item = result_by_path.get(str(video_path.resolve()))
        status = "completed" if result_item and result_item.get("success") else "failed"
        error = result_item.get("error") if result_item else None
        subtasks.append({
            "title": video_path.stem,
            "status": status,
            "error": error,
        })

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "total": total,
        "subtasks": subtasks,
    }

async def run_batch_pipeline(video_urls: list[str], update_progress_fn, delete_after: bool = True, task_id: str | None = None):
    from media_tools.pipeline.download_router import download_by_url as download_router
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    total = len(video_urls)
    if total == 0:
        return {"success_count": 0, "failed_count": 0}

    new_files = []

    # Download phase
    for i, url in enumerate(video_urls):
        await _call_progress(update_progress_fn, 0.4 * (i / total), f"正在下载 ({i+1}/{total})")
        try:
            dl_result = await asyncio.wait_for(
                asyncio.to_thread(download_router, url, 1, True, True, task_id),
                timeout=300,
            )
        except asyncio.TimeoutError:
            logger.error(f"批量下载超时: {url}")
            continue
        if isinstance(dl_result, dict) and dl_result.get('new_files'):
            new_files.extend(dl_result['new_files'])

    if not new_files:
        return {"success_count": 0, "failed_count": total}

    # Transcribe phase (并发批量转写)
    config = load_pipeline_config()
    state_file = Path(f".pipeline_state_{task_id or 'batch_default'}.json")
    orchestrator = create_orchestrator(config, state_file=state_file)

    # 使用批量并发转写
    def _progress_callback(current: int, total: int, video_path: Path, status: str):
        progress = 0.4 + 0.6 * (current / total) if total > 0 else 0.4
        result = update_progress_fn(progress, status)
        if inspect.isawaitable(result):
            _create_managed_task(result)
        elif result is not None:
            logger.warning(f"update_progress_fn 返回非协程: {type(result)}")
        return None

    orchestrator.on_progress = _progress_callback

    video_paths = [Path(f) for f in new_files]
    report = await orchestrator.transcribe_batch(video_paths, resume=False)

    success_count = report.success
    failed_count = report.failed
    successful_paths = {
        str(Path(item["video_path"]).resolve())
        for item in getattr(report, "results", [])
        if item.get("success") and item.get("video_path")
    }

    # 删除已转写的视频
    if delete_after:
        for path in video_paths:
            if str(path.resolve()) not in successful_paths:
                continue
            if path.exists():
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                except OSError as e:
                    logger.error(f"删除视频失败 (DB已更新): {path}, {e}")

    return {"success_count": success_count, "failed_count": failed_count}


async def run_download_only(video_urls: list[str], update_progress_fn, task_id: str | None = None):
    """仅下载视频，不转写"""
    from media_tools.pipeline.download_router import download_by_url as download_router

    total = len(video_urls)
    if total == 0:
        return {"success_count": 0, "failed_count": 0}

    success_count = 0
    failed_count = 0

    for i, url in enumerate(video_urls):
        await _call_progress(update_progress_fn, i / total, f"正在下载 ({i+1}/{total})")
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(download_router, url, 1, True, True, task_id),
                timeout=300,
            )
            if isinstance(result, dict) and result.get("success"):
                success_count += 1
            else:
                failed_count += 1
        except asyncio.TimeoutError:
            logger.error(f"下载超时 {url}")
            failed_count += 1
        except (OSError, RuntimeError, ValueError) as exc:
            logger.error(f"下载失败 {url}: {exc}")
            failed_count += 1

    return {"success_count": success_count, "failed_count": failed_count}
