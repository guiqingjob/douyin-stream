from __future__ import annotations


def resolve_platform(url: str) -> str:
    value = (url or "").lower()
    if "bilibili.com" in value or "b23.tv" in value:
        return "bilibili"
    return "douyin"


def download_by_url(url: str, max_counts: int | None, disable_auto_transcribe: bool, skip_existing: bool):
    platform = resolve_platform(url)
    if platform == "bilibili":
        # B站使用 yt-dlp
        from media_tools.bilibili.core.downloader import download_up_by_url
        return download_up_by_url(url, max_counts=max_counts, skip_existing=skip_existing)
    else:
        # 抖音全部使用 F2（yt-dlp 不支持用户主页）
        from media_tools.douyin.core.downloader import download_by_url as douyin_download
        return douyin_download(url, max_counts, disable_auto_transcribe, skip_existing)