from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger

from media_tools.bilibili.utils.cookies import get_bilibili_cookie_string
from media_tools.bilibili.utils.naming import sanitize_filename

logger = get_logger("bilibili")

ProgressCallback = Callable[[float, str], Any]

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


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

    def hook(d: dict):
        if not progress_cb:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            p = (downloaded / total) if total else 0.0
            progress_cb(min(max(p, 0.0), 1.0), "下载中")
        elif status == "finished":
            progress_cb(1.0, "下载完成")

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
    }

    if cookie:
        ydl_opts["http_headers"] = {"Cookie": cookie}

    if max_counts is not None:
        ydl_opts["playlistend"] = max_counts

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    new_files: list[str] = []
    if isinstance(info, dict):
        requested = info.get("requested_downloads") or []
        for item in requested:
            fp = item.get("filepath")
            if fp and Path(fp).exists():
                new_files.append(str(Path(fp)))

    if not new_files:
        logger.warning("No files downloaded")

    return {"success": True, "new_files": new_files}

