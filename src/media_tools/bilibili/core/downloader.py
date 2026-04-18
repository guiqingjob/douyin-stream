from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger

from media_tools.bilibili.utils.cookies import get_bilibili_cookie_string
from media_tools.bilibili.utils.naming import sanitize_filename

logger = get_logger("bilibili")

# 扩展进度回调：支持详细进度信息
DownloadProgress = dict[str, Any]
ProgressCallback = Callable[[float, str, DownloadProgress], Any]
# 兼容旧的回调签名
LegacyProgressCallback = Callable[[float, str], Any]

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


@dataclass
class UploaderInfo:
    nickname: str
    mid: str
    homepage_url: str


def _format_speed(speed_bytes_per_sec: float) -> str:
    """格式化下载速度"""
    if speed_bytes_per_sec >= 1024 * 1024:
        return f"{speed_bytes_per_sec / (1024 * 1024):.1f} MB/s"
    elif speed_bytes_per_sec >= 1024:
        return f"{speed_bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{speed_bytes_per_sec:.0f} B/s"


def _format_eta(seconds: int | float) -> str:
    """格式化剩余时间"""
    if seconds >= 3600:
        return f"{int(seconds / 3600)}h {int((seconds % 3600) / 60)}m"
    elif seconds >= 60:
        return f"{int(seconds / 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds)}s"


def _build_output_template(base_dir: Path, creator_folder: str, series_folder: str) -> str:
    safe_creator = sanitize_filename(creator_folder) or "bilibili"
    safe_series = sanitize_filename(series_folder) or "全部投稿"
    target_dir = base_dir / safe_creator / safe_series
    target_dir.mkdir(parents=True, exist_ok=True)
    return str(target_dir / "%(title)s__%(id)s__%(format_id)s.%(ext)s")


def download_up_by_url(
    url: str,
    max_counts: int | None = None,
    skip_existing: bool = True,
    progress_cb: ProgressCallback | None = None,
) -> dict:
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp not installed")

    config = get_config()
    downloads_path = config.get_download_path()

    cookie = get_bilibili_cookie_string()

    uploader_info: UploaderInfo | None = None

    def hook(d: dict):
        nonlocal uploader_info
        if not progress_cb:
            return

        # 检测回调函数签名，兼容新旧版本
        try:
            sig = inspect.signature(progress_cb)
            param_count = len(sig.parameters)
        except (ValueError, TypeError):
            param_count = 2  # 默认兼容旧签名

        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            eta = d.get("eta")

            p = (downloaded / total) if total else 0.0
            progress_msg = "下载中"

            # 构建详细进度信息
            extra_info: DownloadProgress = {}
            if total > 0:
                extra_info["total_bytes"] = total
                extra_info["downloaded_bytes"] = downloaded
                extra_info["percent"] = p * 100

            if speed and speed > 0:
                extra_info["speed"] = speed
                speed_str = _format_speed(speed)
                progress_msg = f"下载中 {speed_str}"

            if eta is not None and eta > 0:
                extra_info["eta_seconds"] = eta
                eta_str = _format_eta(eta)
                progress_msg = f"{progress_msg} · 剩余 {eta_str}" if progress_msg != "下载中" else f"剩余 {eta_str}"

            # 根据回调签名调用
            if param_count >= 3:
                progress_cb(min(max(p, 0.0), 1.0), progress_msg, extra_info)
            else:
                progress_cb(min(max(p, 0.0), 1.0), progress_msg)
        elif status == "finished":
            if param_count >= 3:
                progress_cb(1.0, "下载完成", {})
            else:
                progress_cb(1.0, "下载完成")

        # 提取 uploader 信息（从第一个视频条目）
        if uploader_info is None:
            entry = d.get("info", {})
            if entry:
                uploader = entry.get("uploader") or entry.get("uploader_name") or entry.get("channel") or entry.get("channel_id")
                mid = entry.get("uploader_id") or entry.get("channel_id") or entry.get("mid")
                if uploader and mid:
                    uploader_info = UploaderInfo(
                        nickname=uploader,
                        mid=str(mid),
                        homepage_url=f"https://space.bilibili.com/{mid}",
                    )

    ydl_opts: dict[str, Any] = {
        "noplaylist": False,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "overwrites": False,
        "continuedl": True,
        "consoletitle": False,
        "outtmpl": _build_output_template(downloads_path, "bilibili", "全部投稿"),
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "retries": 5,
        "extractor_retries": 5,
        "sleep_interval": 2,
        "max_sleep_interval": 6,
    }

    proxy = os.environ.get("BILIBILI_PROXY", "").strip()
    ydl_opts["proxy"] = proxy if proxy else ""

    headers: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }
    if cookie:
        headers["Cookie"] = cookie
    ydl_opts["http_headers"] = headers

    if max_counts is not None:
        ydl_opts["playlistend"] = max_counts

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # 尝试从 info 中提取 uploader 信息（如果 hook 没有捕获到）
    if uploader_info is None and isinstance(info, dict):
        uploader = info.get("uploader") or info.get("channel") or info.get("uploader_name")
        mid = info.get("uploader_id") or info.get("channel_id") or info.get("mid")
        if uploader and mid:
            uploader_info = UploaderInfo(
                nickname=uploader,
                mid=str(mid),
                homepage_url=f"https://space.bilibili.com/{mid}",
            )

    new_files: list[str] = []
    if isinstance(info, dict):
        requested = info.get("requested_downloads") or []
        for item in requested:
            fp = item.get("filepath")
            if fp and Path(fp).exists():
                new_files.append(str(Path(fp)))

    if not new_files:
        logger.warning("No files downloaded")

    result = {"success": True, "new_files": new_files}
    if uploader_info:
        result["uploader"] = {
            "nickname": uploader_info.nickname,
            "mid": uploader_info.mid,
            "homepage_url": uploader_info.homepage_url,
        }
    return result
