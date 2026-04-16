from __future__ import annotations


def resolve_platform(url: str) -> str:
    value = (url or "").lower()
    if "bilibili.com" in value or "b23.tv" in value:
        return "bilibili"
    return "douyin"


def download_by_url(url: str, max_counts: int | None, disable_auto_transcribe: bool, skip_existing: bool):
    platform = resolve_platform(url)
    if platform == "bilibili":
        from media_tools.bilibili.core.downloader import download_up_by_url
        return download_up_by_url(url, max_counts=max_counts, skip_existing=skip_existing)
    from media_tools.douyin.core.downloader import download_by_url as douyin_download_by_url
    return douyin_download_by_url(url, max_counts=max_counts, disable_auto_transcribe=disable_auto_transcribe, skip_existing=skip_existing)

