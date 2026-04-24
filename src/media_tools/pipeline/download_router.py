from __future__ import annotations

import asyncio
import re


def resolve_platform(url: str) -> str:
    value = (url or "").lower()
    if "bilibili.com" in value or "b23.tv" in value:
        return "bilibili"
    return "douyin"


def is_aweme_url(url: str) -> bool:
    """判断是否为抖音单个视频链接（/video/xxx），而非用户主页链接（/user/xxx）"""
    return bool(re.search(r'douyin\.com/video/\d+', url))


def download_by_url(url: str, max_counts: int | None, disable_auto_transcribe: bool, skip_existing: bool, task_id: str | None = None):
    platform = resolve_platform(url)
    if platform == "bilibili":
        from media_tools.bilibili.core.downloader import download_up_by_url
        return download_up_by_url(url, max_counts=max_counts, skip_existing=skip_existing, task_id=task_id, disable_auto_transcribe=disable_auto_transcribe)
    else:
        if is_aweme_url(url):
            # 单个视频链接 → 走 download_aweme_by_url（async，用 asyncio.run 包装）
            from media_tools.douyin.core.downloader import download_aweme_by_url
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # 已在事件循环中（不应发生，因为 to_thread 在新线程里），用新线程跑
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, download_aweme_by_url(url)).result()
            else:
                return asyncio.run(download_aweme_by_url(url))
        else:
            # 用户主页链接 → 走 download_by_url（用 SecUserIdFetcher）
            from media_tools.douyin.core.downloader import download_by_url as douyin_download
            return douyin_download(url, max_counts, disable_auto_transcribe, skip_existing, task_id=task_id)