"""
抖音视频下载模块 - 基于 yt-dlp
替换原有 F2 实现，解决无法停止、无增量检查等问题
支持暂停/恢复功能
"""

from __future__ import annotations

import inspect
import re
import sqlite3
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger
from media_tools.bilibili.utils.naming import sanitize_filename

logger = get_logger("douyin_ytdlp")

# 扩展进度回调：支持详细进度信息
DownloadProgress = dict[str, Any]
ProgressCallback = Callable[[float, str, DownloadProgress], Any]
LegacyProgressCallback = Callable[[float, str], Any]

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


@dataclass
class DouyinUploaderInfo:
    nickname: str
    sec_user_id: str
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


def _build_output_template(base_dir: Path, creator_folder: str) -> str:
    """构建输出模板"""
    safe_creator = sanitize_filename(creator_folder) or "douyin"
    target_dir = base_dir / safe_creator
    target_dir.mkdir(parents=True, exist_ok=True)
    return str(target_dir / "%(title)s__%(id)s__%(format_id)s.%(ext)s")


def _parse_douyin_url(url: str) -> dict | None:
    """解析抖音 URL，返回类型和 ID"""
    url = url.strip()

    # 视频 URL: https://www.douyin.com/video/7509282774827421965
    video_match = re.search(r'douyin\.com/video/(\d+)', url)
    if video_match:
        return {"type": "video", "id": video_match.group(1)}

    # 用户主页: https://www.douyin.com/user/MS4wLjABAAAxxx 或 https://www.douyin.com/user/uid
    user_match = re.search(r'douyin\.com/user/([A-Za-z0-9_-]+)', url)
    if user_match:
        sec_user_id = user_match.group(1)
        # 如果是 MS4w 开头的，那是 sec_user_id
        if sec_user_id.startswith("MS4w"):
            return {"type": "user_sec", "id": sec_user_id}
        else:
            return {"type": "user_uid", "id": sec_user_id}

    return None


def _get_download_archive_path(config) -> Path:
    """获取增量下载记录文件路径"""
    db_dir = config.get_db_path().parent
    archive_path = db_dir / "download_archive.txt"
    return archive_path


# 全局暂停控制字典 - task_id -> PauseController
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
                # 在 macOS 上使用 SIGSTOP 暂停进程
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
        self._paused.set()  # 允许线程继续以便优雅退出
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
    """注册新的暂停控制器"""
    with _pause_lock:
        controller = PauseController(task_id)
        _pause_controllers[task_id] = controller
        return controller


def get_pause_controller(task_id: str) -> PauseController | None:
    """获取暂停控制器"""
    with _pause_lock:
        return _pause_controllers.get(task_id)


def unregister_pause_controller(task_id: str):
    """注销暂停控制器"""
    with _pause_lock:
        _pause_controllers.pop(task_id, None)


def pause_task(task_id: str):
    """暂停指定任务"""
    controller = get_pause_controller(task_id)
    if controller:
        controller.pause()


def resume_task(task_id: str):
    """恢复指定任务"""
    controller = get_pause_controller(task_id)
    if controller:
        controller.resume()


def cancel_task_download(task_id: str):
    """取消指定任务"""
    controller = get_pause_controller(task_id)
    if controller:
        controller.cancel()


def download_by_url(
    url: str,
    max_counts: int | None = None,
    disable_auto_transcribe: bool = False,
    skip_existing: bool = True,
    progress_cb: ProgressCallback | None = None,
) -> dict:
    """
    通过 URL 下载抖音视频

    Args:
        url: 抖音视频或用户主页 URL
        max_counts: 最大下载数量（用户主页时有效）
        disable_auto_transcribe: 是否禁用自动转写（未使用，保留兼容）
        skip_existing: 是否跳过已下载（使用 download archive）
        progress_cb: 进度回调

    Returns:
        dict: 包含 success, new_files, uploader 等信息
    """
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp not installed")

    config = get_config()
    downloads_path = config.get_download_path()
    cookie = config.get_cookie()

    parsed = _parse_douyin_url(url)
    if not parsed:
        raise ValueError(f"无法解析抖音 URL: {url}")

    download_type = parsed["type"]

    # 获取下载 archive 文件路径（用于增量下载）
    archive_path = _get_download_archive_path(config)

    uploader_info: DouyinUploaderInfo | None = None

    def hook(d: dict):
        nonlocal uploader_info
        if not progress_cb:
            return

        # 检测回调函数签名，兼容新旧版本
        try:
            sig = inspect.signature(progress_cb)
            param_count = len(sig.parameters)
        except (ValueError, TypeError):
            param_count = 2

        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            eta = d.get("eta")

            p = (downloaded / total) if total else 0.0
            progress_msg = "下载中"

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

            if param_count >= 3:
                progress_cb(min(max(p, 0.0), 1.0), progress_msg, extra_info)  # type: ignore[call-arg]
            else:
                progress_cb(min(max(p, 0.0), 1.0), progress_msg)  # type: ignore[call-arg]

        elif status == "finished":
            if param_count >= 3:
                progress_cb(1.0, "下载完成", {})  # type: ignore[call-arg]
            else:
                progress_cb(1.0, "下载完成")  # type: ignore[call-arg]

        # 提取 uploader 信息
        if uploader_info is None:
            entry = d.get("info", {})
            if entry:
                nickname = entry.get("uploader") or entry.get("nickname") or entry.get("uploader_name") or entry.get("channel")
                sec_user_id = entry.get("sec_user_id") or entry.get("uploader_id") or entry.get("creator_sec_user_id", "")
                if nickname or sec_user_id:
                    sec_user_id = str(sec_user_id)
                    homepage_url = f"https://www.douyin.com/user/{sec_user_id}" if sec_user_id.startswith("MS4w") else f"https://www.douyin.com/user/{sec_user_id}"
                    uploader_info = DouyinUploaderInfo(
                        nickname=nickname or "未知",
                        sec_user_id=sec_user_id,
                        homepage_url=homepage_url,
                    )

    # 确定输出目录和模板
    creator_folder = "douyin"
    if download_type == "user_sec" or download_type == "user_uid":
        # 用户主页，输出到以用户命名的文件夹
        creator_folder = "douyin_user"

    output_template = _build_output_template(downloads_path, creator_folder)

    ydl_opts: dict[str, Any] = {
        "noplaylist": False,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "overwrites": False,
        "continuedl": True,
        "consoletitle": False,
        "outtmpl": output_template,
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "retries": 5,
        "extractor_retries": 5,
        "sleep_interval": 2,
        "max_sleep_interval": 6,
    }

    # 增量下载配置
    if skip_existing and archive_path.exists():
        ydl_opts["download_archive"] = str(archive_path)

    # Cookie 配置 - 转换为 Netscape 格式
    cookie_file = None
    if cookie:
        import tempfile
        # 转换为 Netscape 格式
        cookie_lines = ["# Netscape HTTP Cookie File"]
        # 解析 cookie 字符串并转换为 Netscape 格式
        for part in cookie.split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                # domain, flag, path, secure, expiration, name, value
                cookie_lines.append(f".douyin.com\tTRUE\t/\tFALSE\t0\t{key}\t{value}")
        cookie_content = "\n".join(cookie_lines)
        cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        cookie_file.write(cookie_content)
        cookie_file.close()
        ydl_opts["cookiefile"] = cookie_file.name

    # 用户主页下载数量限制
    if download_type in ("user_sec", "user_uid") and max_counts is not None:
        ydl_opts["playlistend"] = max_counts

    # User-Agent
    ydl_opts["http_headers"] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # 尝试从 info 中提取 uploader 信息
        if uploader_info is None and isinstance(info, dict):
            nickname = info.get("uploader") or info.get("nickname") or info.get("channel")
            sec_user_id = info.get("sec_user_id") or ""
            if nickname or sec_user_id:
                sec_user_id = str(sec_user_id)
                homepage_url = f"https://www.douyin.com/user/{sec_user_id}" if sec_user_id.startswith("MS4w") else f"https://www.douyin.com/user/{sec_user_id}"
                uploader_info = DouyinUploaderInfo(
                    nickname=nickname or "未知",
                    sec_user_id=sec_user_id,
                    homepage_url=homepage_url,
                )

    finally:
        # 清理临时 cookie 文件
        if cookie and "cookiefile" in ydl_opts:
            try:
                import os
                os.unlink(ydl_opts["cookiefile"])
            except Exception:
                pass

    # 收集下载的文件
    new_files: list[str] = []
    if isinstance(info, dict):
        # 单个视频
        if info.get("filepath") and Path(info["filepath"]).exists():
            new_files.append(str(Path(info["filepath"])))
        # 播放列表
        requested = info.get("requested_downloads") or []
        for item in requested:
            fp = item.get("filepath")
            if fp and Path(fp).exists():
                new_files.append(str(Path(fp)))

    # 也扫描输出目录获取新文件
    output_dir = Path(output_template).parent
    if output_dir.exists():
        for video_file in output_dir.glob("*.mp4"):
            if str(video_file) not in new_files:
                new_files.append(str(video_file))

    # 将下载记录写入 archive（用于增量下载）
    if skip_existing and new_files:
        with open(archive_path, "a", encoding="utf-8") as archive_file:
            for fp in new_files:
                # 尝试从文件名提取 aweme_id
                stem = Path(fp).stem
                aweme_ids = re.findall(r'\d{19,}', stem)
                for aweme_id in aweme_ids:
                    archive_file.write(f"douyin {aweme_id}\n")

    if not new_files:
        logger.warning("No files downloaded")

    result: dict[str, Any] = {"success": True, "new_files": new_files}

    if uploader_info:
        result["uploader"] = {
            "nickname": uploader_info.nickname,
            "sec_user_id": uploader_info.sec_user_id,
            "homepage_url": uploader_info.homepage_url,
        }

    # 尝试从 info 中提取 uid（兼容用户主页）
    if download_type in ("user_sec", "user_uid"):
        if isinstance(info, dict):
            result["uid"] = info.get("uploader_id") or info.get("creator_sec_user_id") or parsed.get("id")
            result["nickname"] = info.get("uploader") or info.get("nickname") or parsed.get("id")

    return result


def download_by_url_pausable(
    url: str,
    task_id: str,
    max_counts: int | None = None,
    skip_existing: bool = True,
    progress_cb: ProgressCallback | None = None,
) -> dict:
    """
    通过 URL 下载抖音视频（支持暂停/恢复）
    使用子进程运行 yt-dlp，支持通过 task_id 暂停/恢复

    Args:
        url: 抖音视频或用户主页 URL
        task_id: 任务 ID（用于暂停/恢复控制）
        max_counts: 最大下载数量（用户主页时有效）
        skip_existing: 是否跳过已下载
        progress_cb: 进度回调

    Returns:
        dict: 包含 success, new_files, uploader 等信息
    """
    from yt_dlp import YoutubeDL

    config = get_config()
    downloads_path = config.get_download_path()
    cookie = config.get_cookie()

    parsed = _parse_douyin_url(url)
    if not parsed:
        raise ValueError(f"无法解析抖音 URL: {url}")

    download_type = parsed["type"]
    archive_path = _get_download_archive_path(config)

    # 注册暂停控制器
    controller = register_pause_controller(task_id)

    # 确定输出目录和模板
    creator_folder = "douyin"
    if download_type == "user_sec" or download_type == "user_uid":
        creator_folder = "douyin_user"

    output_template = _build_output_template(downloads_path, creator_folder)

    ydl_opts: dict[str, Any] = {
        "noplaylist": False,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "overwrites": False,
        "continuedl": True,
        "consoletitle": False,
        "outtmpl": output_template,
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "retries": 5,
        "extractor_retries": 5,
        "sleep_interval": 2,
        "max_sleep_interval": 6,
        "nocheckcertificate": True,
    }

    if skip_existing and archive_path.exists():
        ydl_opts["download_archive"] = str(archive_path)

    # 构建 yt-dlp 命令
    cmd = ["yt-dlp"]
    for k, v in ydl_opts.items():
        if v is True:
            cmd.append(f"--{k}")
        elif v is False:
            cmd.append(f"--no-{k}")
        elif isinstance(v, list):
            for item in v:
                cmd.append(f"--{k}")
                cmd.append(str(item))
        elif v is not None:
            cmd.append(f"--{k}")
            cmd.append(str(v))

    cmd.append(url)

    # 处理 cookie - 转换为 Netscape 格式
    cookie_file = None
    if cookie:
        import tempfile
        # 转换为 Netscape 格式
        cookie_lines = ["# Netscape HTTP Cookie File"]
        for part in cookie.split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                cookie_lines.append(f".douyin.com\tTRUE\t/\tFALSE\t0\t{key}\t{value}")
        cookie_content = "\n".join(cookie_lines)
        cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        cookie_file.write(cookie_content)
        cookie_file.close()
        cmd.insert(1, "--cookiefile")
        cmd.insert(2, cookie_file.name)

    # 用户主页下载数量限制
    if download_type in ("user_sec", "user_uid") and max_counts is not None:
        cmd.insert(2, "--playlist-end")
        cmd.insert(3, str(max_counts))

    # 添加 User-Agent
    cmd.insert(1, "--user-agent")
    cmd.insert(2, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")
    cmd.insert(3, "--add-header")
    cmd.insert(4, "Referer:https://www.douyin.com/")

    uploader_info: DouyinUploaderInfo | None = None
    new_files: list[str] = []

    try:
        # 使用 subprocess 运行，支持暂停
        logger.info(f"Starting download: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        controller.set_process(proc)

        # 监控输出并处理暂停
        import select

        while True:
            # 检查是否被取消
            if controller.is_cancelled():
                logger.info(f"Task {task_id} cancelled by user")
                break

            # 检查暂停状态
            controller.check_pause()

            # 非阻塞读取 stdout
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)  # type: ignore[arg-type]
            if ready:
                line = proc.stdout.readline()  # type: ignore[union-attr]
                if line:
                    # 解析进度
                    if progress_cb and "%" in line:  # type: ignore[truthy-function]
                        # 尝试提取进度百分比
                        import re as re2
                        percent_match = re2.search(r'(\d+\.?\d*)%', line)
                        speed_match = re2.search(r'(\d+\.?\d*\s*[KMG]?B/s)', line)
                        eta_match = re2.search(r'ETA\s*(\d+:\d+)', line)

                        p = 0.0
                        msg = "下载中"
                        extra: dict = {}

                        if percent_match:
                            p = float(percent_match.group(1)) / 100
                            msg = f"下载中 {percent_match.group(1)}%"
                            extra["percent"] = float(percent_match.group(1))

                        if speed_match:
                            msg = f"{msg} · {speed_match.group(1)}"
                            extra["speed"] = speed_match.group(1)

                        if eta_match:
                            msg = f"{msg} · 剩余 {eta_match.group(1)}"

                        if progress_cb:  # type: ignore[truthy-function]
                            progress_cb(min(max(p, 0.0), 1.0), msg, extra)

            # 检查进程是否结束
            if proc.poll() is not None:
                break

        # 等待进程结束
        proc.wait()

        # 读取 stderr（如果有错误）
        stderr = proc.stderr.read() if proc.stderr else ""
        if proc.returncode != 0 and stderr:
            logger.warning(f"yt-dlp stderr: {stderr}")

    finally:
        # 清理
        if cookie_file:
            try:
                import os
                os.unlink(cookie_file.name)
            except Exception:
                pass
        unregister_pause_controller(task_id)

    # 收集下载的文件
    output_dir = Path(output_template).parent
    if output_dir.exists():
        for f in output_dir.glob("*.mp4"):
            if str(f) not in new_files:
                new_files.append(str(f))

    # 写入 archive
    if skip_existing and new_files:
        with open(archive_path, "a", encoding="utf-8") as archive_file:
            for fp in new_files:
                stem = Path(fp).stem
                aweme_ids = re.findall(r'\d{19,}', stem)
                for aweme_id in aweme_ids:
                    archive_file.write(f"douyin {aweme_id}\n")

    result: dict[str, Any] = {"success": True, "new_files": new_files}

    return result