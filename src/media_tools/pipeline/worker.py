import asyncio
from pathlib import Path
from media_tools.logger import get_logger

logger = get_logger('pipeline')

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm'}


def run_local_transcribe(file_paths: list[str], update_progress_fn=None, delete_after: bool = False):
    """转写本地视频文件（不经过下载步骤）"""
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator

    valid_paths = []
    for p in file_paths:
        path = Path(p)
        if path.exists() and path.suffix.lower() in VIDEO_EXTENSIONS:
            valid_paths.append(path)

    if not valid_paths:
        return {"success_count": 0, "failed_count": 0, "total": 0}

    config = load_pipeline_config()
    orchestrator = create_orchestrator(config, creator_folder_override="本地上传")

    success_count = 0
    failed_count = 0
    total = len(valid_paths)

    async def _run():
        nonlocal success_count, failed_count
        for i, video_path in enumerate(valid_paths):
            if update_progress_fn:
                update_progress_fn(i / total, f"正在转写 {video_path.name} ({i+1}/{total})")
            try:
                result = await orchestrator.transcribe_with_retry(video_path)
                if result.success:
                    success_count += 1
                    if delete_after and video_path.exists():
                        try:
                            video_path.unlink()
                        except Exception as e:
                            logger.warning(f"无法删除视频 {video_path}: {e}")
                else:
                    failed_count += 1
            except Exception as exc:
                logger.error(f"转写失败 {video_path}: {exc}")
                failed_count += 1

    asyncio.run(_run())
    return {"success_count": success_count, "failed_count": failed_count, "total": total}


def run_pipeline_for_user(url: str, max_counts: int, update_progress_fn, delete_after: bool = True):
    from media_tools.douyin.core.downloader import download_by_url
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator
    
    update_progress_fn(0.1, "正在下载视频...")
    
    # 1. Download
    dl_result = download_by_url(url, max_counts=max_counts)
    new_files = dl_result.get('new_files', []) if isinstance(dl_result, dict) else []
    
    if not new_files:
        update_progress_fn(1.0, "没有下载到新视频")
        return {"success_count": 0, "failed_count": 0}
        
    update_progress_fn(0.4, f"下载完成，准备转写 {len(new_files)} 个视频...")
    
    # 2. Transcribe
    config = load_pipeline_config()
    orchestrator = create_orchestrator(config)
    
    success_count = 0
    failed_count = 0
    
    async def _run_batch():
        nonlocal success_count, failed_count
        total = len(new_files)
        for i, file_path in enumerate(new_files):
            progress = 0.4 + 0.6 * (i / total)
            update_progress_fn(progress, f"正在转写 ({i+1}/{total})")
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
                
    asyncio.run(_run_batch())
    update_progress_fn(1.0, "全自动流水线完成")
    
    return {
        "success_count": success_count,
        "failed_count": failed_count
    }

def run_batch_pipeline(video_urls: list[str], update_progress_fn, delete_after: bool = True):
    from media_tools.douyin.core.downloader import download_by_url
    from media_tools.pipeline.config import load_pipeline_config
    from media_tools.pipeline.orchestrator_v2 import create_orchestrator
    
    total = len(video_urls)
    new_files = []
    
    # Download phase
    for i, url in enumerate(video_urls):
        update_progress_fn(0.4 * (i/total), f"正在下载 ({i+1}/{total})")
        dl_result = download_by_url(url, max_counts=1) # Download single video
        if isinstance(dl_result, dict) and dl_result.get('new_files'):
            new_files.extend(dl_result['new_files'])
            
    if not new_files:
        return {"success_count": 0, "failed_count": total}

    # Transcribe phase
    config = load_pipeline_config()
    orchestrator = create_orchestrator(config)
    success_count = 0
    failed_count = 0
    
    import asyncio
    from pathlib import Path
    async def _run_batch():
        nonlocal success_count, failed_count
        for i, file_path in enumerate(new_files):
            update_progress_fn(0.4 + 0.6 * (i/len(new_files)), f"正在转写 ({i+1}/{len(new_files)})")
            try:
                await orchestrator.transcribe_with_retry(file_path)
                success_count += 1
                if delete_after:
                    Path(file_path).unlink(missing_ok=True)
            except Exception:
                failed_count += 1
    
    asyncio.run(_run_batch())
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