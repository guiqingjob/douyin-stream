import asyncio
import inspect
import hashlib
from pathlib import Path
from media_tools.logger import get_logger
from media_tools.pipeline.media_extensions import MEDIA_EXTENSIONS

logger = get_logger('pipeline')


async def _call_progress(update_progress_fn, progress: float, msg: str) -> None:
    if not update_progress_fn:
        return
    result = update_progress_fn(progress, msg)
    if inspect.isawaitable(result):
        await result


def filter_supported_media_paths(file_paths: list[str]) -> list[Path]:
    valid_paths: list[Path] = []
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists() and path.suffix.lower() in MEDIA_EXTENSIONS:
            valid_paths.append(path)
    return valid_paths


def _local_asset_id(file_path: Path) -> str:
    resolved = str(file_path.resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:24]
    return f"local:{digest}"


def run_local_transcribe(file_paths: list[str], update_progress_fn=None, delete_after: bool = False):
    """转写本地视频文件（不经过下载步骤）"""
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    valid_paths = filter_supported_media_paths(file_paths)

    if not valid_paths:
        return {"success_count": 0, "failed_count": 0, "total": 0}

    config = load_pipeline_config()
    orchestrator = create_orchestrator(config, creator_folder_override="本地上传")
    output_root = Path(config.output_dir).resolve()

    success_count = 0
    failed_count = 0
    total = len(valid_paths)

    async def _run():
        nonlocal success_count, failed_count
        await _call_progress(update_progress_fn, 0.0, f"准备转写 {total} 个文件（并发 {config.concurrency}）")
        try:
            report = await orchestrator.transcribe_batch(valid_paths, resume=True)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"批量本地转写失败: {exc}")
            failed_count = total
            return

        from media_tools.db.core import get_db_connection

        for item in report.results:
            video_path = Path(item["video_path"])
            if item.get("success"):
                success_count += 1
                try:
                    transcript_path = item.get("transcript_path")
                    transcript_name = ""
                    if transcript_path:
                        try:
                            transcript_name = str(Path(transcript_path).resolve().relative_to(output_root))
                        except Exception:
                            transcript_name = str(Path(transcript_path).name)
                    with get_db_connection() as conn:
                        conn.execute(
                            """
                            UPDATE media_assets
                            SET transcript_path = ?, transcript_status = 'completed', update_time = CURRENT_TIMESTAMP
                            WHERE asset_id = ?
                            """,
                            (transcript_name, _local_asset_id(video_path)),
                        )
                        conn.commit()
                except Exception:
                    pass
                if delete_after and video_path.exists():
                    try:
                        video_path.unlink()
                    except Exception as e:  # noqa: BLE001
                        logger.warning(f"无法删除视频 {video_path}: {e}")
            else:
                failed_count += 1

            completed = success_count + failed_count
            await _call_progress(
                update_progress_fn,
                completed / total,
                f"已处理 {completed}/{total}",
            )

    asyncio.run(_run())
    return {"success_count": success_count, "failed_count": failed_count, "total": total}


async def run_pipeline_for_user(url: str, max_counts: int, update_progress_fn, delete_after: bool = True):
    from media_tools.pipeline.download_router import download_by_url as download_by_url_router
    from media_tools.pipeline.download_router import resolve_platform
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator
    
    await _call_progress(update_progress_fn, 0.1, "正在下载视频...")
    
    # 1. Download
    if resolve_platform(url) == "bilibili":
        download_fn = download_by_url_router
    else:
        from media_tools.douyin.core.downloader import download_by_url as download_fn
    dl_result = await asyncio.to_thread(download_fn, url, max_counts, True, True)
    new_files = dl_result.get('new_files', []) if isinstance(dl_result, dict) else []
    
    if not new_files:
        await _call_progress(update_progress_fn, 1.0, "没有下载到新视频")
        return {"success_count": 0, "failed_count": 0}
        
    await _call_progress(update_progress_fn, 0.4, f"下载完成，准备转写 {len(new_files)} 个视频...")
    
    # 2. Transcribe
    config = load_pipeline_config()
    orchestrator = create_orchestrator(config)
    
    success_count = 0
    failed_count = 0
    
    total = len(new_files)
    for i, file_path in enumerate(new_files):
        progress = 0.4 + 0.6 * (i / total)
        await _call_progress(update_progress_fn, progress, f"正在转写 ({i+1}/{total})")
        try:
            await orchestrator.transcribe_with_retry(file_path)
            success_count += 1
            if delete_after:
                try:
                    Path(file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"无法删除视频 {file_path}: {e}")
        except Exception as exc:
            logger.error(f"转写失败 {file_path}: {exc}")
            failed_count += 1

    await _call_progress(update_progress_fn, 1.0, "全自动流水线完成")
    
    return {
        "success_count": success_count,
        "failed_count": failed_count
    }

async def run_batch_pipeline(video_urls: list[str], update_progress_fn, delete_after: bool = True):
    from media_tools.pipeline.download_router import download_by_url
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator
    
    total = len(video_urls)
    new_files = []
    
    # Download phase
    for i, url in enumerate(video_urls):
        await _call_progress(update_progress_fn, 0.4 * (i/total), f"正在下载 ({i+1}/{total})")
        dl_result = await asyncio.to_thread(download_by_url, url, 1, True, True)
        if isinstance(dl_result, dict) and dl_result.get('new_files'):
            new_files.extend(dl_result['new_files'])
            
    if not new_files:
        return {"success_count": 0, "failed_count": total}

    # Transcribe phase
    config = load_pipeline_config()
    orchestrator = create_orchestrator(config)
    success_count = 0
    failed_count = 0
    
    for i, file_path in enumerate(new_files):
        await _call_progress(update_progress_fn, 0.4 + 0.6 * (i/len(new_files)), f"正在转写 ({i+1}/{len(new_files)})")
        try:
            await orchestrator.transcribe_with_retry(file_path)
            success_count += 1
            if delete_after:
                Path(file_path).unlink(missing_ok=True)
        except Exception:
            failed_count += 1
    return {"success_count": success_count, "failed_count": failed_count}


async def run_download_only(video_urls: list[str], update_progress_fn):
    """仅下载视频，不转写"""
    from media_tools.douyin.core.downloader import download_aweme_by_url

    total = len(video_urls)
    success_count = 0
    failed_count = 0

    for i, url in enumerate(video_urls):
        await update_progress_fn(i / total, f"正在下载 ({i+1}/{total})")
        try:
            result = await asyncio.to_thread(download_aweme_by_url, url)
            if isinstance(result, dict) and result.get("success"):
                success_count += 1
            else:
                failed_count += 1
        except Exception as exc:
            logger.error(f"下载失败 {url}: {exc}")
            failed_count += 1

    return {"success_count": success_count, "failed_count": failed_count}
