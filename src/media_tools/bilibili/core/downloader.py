from __future__ import annotations

import atexit
import inspect
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Generator

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger

from media_tools.bilibili.utils.cookies import get_bilibili_cookie_string
from media_tools.bilibili.utils.naming import sanitize_filename

logger = get_logger("bilibili")

# --- 临时文件安全管理（复用 douyin_ytdlp 的实现）---
_temp_files: set[str] = set()
_temp_files_lock = threading.Lock()


def _cleanup_temp_files() -> None:
    """进程退出时清理所有临时文件"""
    with _temp_files_lock:
        for path_str in list(_temp_files):
            try:
                if os.path.exists(path_str):
                    os.unlink(path_str)
                    logger.debug(f"Cleaned up temp file: {path_str}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {path_str}: {e}")
        _temp_files.clear()


def _register_temp_file(path_str: str) -> None:
    """注册临时文件到清理列表"""
    with _temp_files_lock:
        _temp_files.add(path_str)


def _unregister_temp_file(path_str: str) -> None:
    """从清理列表移除（已清理时调用）"""
    with _temp_files_lock:
        _temp_files.discard(path_str)


def _cleanup_on_signal(signum, frame) -> None:
    """信号处理时清理临时文件"""
    _cleanup_temp_files()
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


# 注册进程退出清理
atexit.register(_cleanup_temp_files)
signal.signal(signal.SIGTERM, _cleanup_on_signal)
signal.signal(signal.SIGINT, _cleanup_on_signal)


@contextmanager
def managed_temp_file(mode: str = 'w', suffix: str = '.txt', dir: str | None = None) -> Generator[tuple, None, None]:
    """
    安全的临时文件上下文管理器（同 douyin_ytdlp）

    - 使用 delete=True（自动删除）
    - 显式在 finally 中 close + unlink（双重保险）
    - mode=0o600 权限，防止其他用户读取
    - 注册到 atexit 清理列表（进程崩溃时也能清理）
    """
    import sys
    if sys.platform == 'win32':
        fd, path_str = tempfile.mkstemp(suffix=suffix, dir=dir, text=True)
        os.chmod(path_str, 0o600)
        f = os.fdopen(fd, mode)
    else:
        f = tempfile.NamedTemporaryFile(
            mode=mode, suffix=suffix, dir=dir,
            delete=True,
        )
        path_str = f.name
        os.chmod(path_str, 0o600)

    _register_temp_file(path_str)

    try:
        yield f, path_str
    finally:
        try:
            f.close()
        except Exception:
            pass
        try:
            if os.path.exists(path_str):
                os.unlink(path_str)
                _unregister_temp_file(path_str)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {path_str}: {e}")

# 扩展进度回调：支持详细进度信息
DownloadProgress = dict[str, Any]
ProgressCallback = Callable[[float, str, DownloadProgress], Any]
# 兼容旧的回调签名
LegacyProgressCallback = Callable[[float, str], Any]

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


# 全局暂停控制字典
_pause_controllers: dict[str, "PauseController"] = {}
_pause_lock = threading.Lock()


class PauseController:
    """暂停控制器，支持暂停/恢复下载"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._paused = threading.Event()
        self._paused.set()  # 初始不暂停
        self._cancelled = threading.Event()
        self._process: subprocess.Popen | None = None

    def pause(self):
        """暂停下载"""
        self._paused.clear()
        if self._process and self._process.poll() is None:
            try:
                if hasattr(signal, 'SIGSTOP'):
                    self._process.send_signal(signal.SIGSTOP)
                logger.info(f"Task {self.task_id} paused")
            except Exception as e:
                logger.warning(f"Failed to pause task {self.task_id}: {e}")

    def resume(self):
        """恢复下载"""
        self._paused.set()
        if self._process and self._process.poll() is None:
            try:
                if hasattr(signal, 'SIGCONT'):
                    self._process.send_signal(signal.SIGCONT)
                logger.info(f"Task {self.task_id} resumed")
            except Exception as e:
                logger.warning(f"Failed to resume task {self.task_id}: {e}")

    def cancel(self):
        """取消下载"""
        self._cancelled.set()
        self._paused.set()
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                logger.info(f"Task {self.task_id} cancelled")
            except Exception as e:
                logger.warning(f"Failed to cancel task {self.task_id}: {e}")

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def check_pause(self):
        """检查是否需要暂停（阻塞直到恢复）"""
        self._paused.wait()

    def set_process(self, proc: subprocess.Popen):
        self._process = proc


def register_pause_controller(task_id: str) -> PauseController:
    with _pause_lock:
        controller = PauseController(task_id)
        _pause_controllers[task_id] = controller
        return controller


def get_pause_controller(task_id: str) -> PauseController | None:
    with _pause_lock:
        return _pause_controllers.get(task_id)


def unregister_pause_controller(task_id: str):
    with _pause_lock:
        _pause_controllers.pop(task_id, None)


def pause_task(task_id: str):
    controller = get_pause_controller(task_id)
    if controller:
        controller.pause()


def resume_task(task_id: str):
    controller = get_pause_controller(task_id)
    if controller:
        controller.resume()


def cancel_task_download(task_id: str):
    controller = get_pause_controller(task_id)
    if controller:
        controller.cancel()


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
                progress_cb(min(max(p, 0.0), 1.0), progress_msg, extra_info)  # type: ignore[call-arg]
            else:
                progress_cb(min(max(p, 0.0), 1.0), progress_msg)  # type: ignore[call-arg]
        elif status == "finished":
            if param_count >= 3:
                progress_cb(1.0, "下载完成", {})  # type: ignore[call-arg]
            else:
                progress_cb(1.0, "下载完成")  # type: ignore[call-arg]

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

    # Cookie 配置 - 转换为 Netscape 格式文件
    cookie_file = None
    if cookie:
        import tempfile
        cookie_lines = ["# Netscape HTTP Cookie File"]
        for part in cookie.split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                cookie_lines.append(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{key}\t{value}")
        cookie_content = "\n".join(cookie_lines)
        # 使用安全的临时文件管理器
        with managed_temp_file(mode='w', suffix='.txt') as (f, cookie_path):
            f.write(cookie_content)
        ydl_opts["cookiefile"] = cookie_path

    headers: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }
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

    # 清理临时 cookie 文件
    if cookie_file:
        try:
            import os as os_module
            os_module.unlink(cookie_file.name)
        except Exception:
            pass

    result = {"success": True, "new_files": new_files}
    if uploader_info:
        result["uploader"] = {
            "nickname": uploader_info.nickname,
            "mid": uploader_info.mid,
            "homepage_url": uploader_info.homepage_url,
        }
    return result
