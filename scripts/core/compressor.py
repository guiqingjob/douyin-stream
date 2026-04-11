#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频压缩模块
"""

import subprocess
import sys
from pathlib import Path

from .ui import (
    error,
    format_size,
    info,
    print_header,
    print_status,
    success,
    warning,
)
from .config_mgr import get_config


def check_ffmpeg():
    """检查 ffmpeg 是否安装"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _get_video_info(video_path):
    """获取视频信息"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(video_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            import json

            info_data = json.loads(result.stdout)
            size = int(info_data["format"]["size"])
            duration = float(info_data["format"]["duration"])
            video_stream = next(
                (s for s in info_data.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )
            height = int(video_stream.get("height", 0)) if video_stream else 0
            return {"size": size, "duration": duration, "height": height}
    except Exception:
        pass
    return None


def _compress_video(input_path, output_path, crf=32, preset="fast"):
    """
    压缩单个视频

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        crf: 压缩质量
        preset: 压缩速度

    Returns:
        (success, original_size, compressed_size) 或 None（跳过）
    """
    info_data = _get_video_info(input_path)
    if not info_data:
        return None

    original_size = info_data["size"]
    height = info_data.get("height", 0)

    # 跳过小文件（< 5MB）
    if original_size < 5 * 1024 * 1024:
        return None

    # 跳过低分辨率（< 720p）
    if height > 0 and height < 720:
        return None

    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-y",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return False

    compressed_info = _get_video_info(output_path)
    compressed_size = compressed_info["size"] if compressed_info else 0

    return True, original_size, compressed_size


def compress_user_dir(user_folder, crf=32, preset="fast", replace=True):
    """
    压缩指定用户目录的视频

    Args:
        user_folder: 用户文件夹名
        crf: 压缩质量
        preset: 压缩速度
        replace: 是否替换原文件

    Returns:
        (success, skipped, failed) 计数
    """
    config = get_config()
    downloads_path = config.get_download_path()
    user_dir = downloads_path / user_folder

    if not user_dir.exists():
        print(error(f"目录不存在: {user_dir}"))
        return 0, 0, 0

    mp4_files = list(user_dir.glob("*.mp4"))
    if not mp4_files:
        print(info(f"没有找到视频文件: {user_dir}"))
        return 0, 0, 0

    print(info(f"处理用户目录: {user_folder}"))
    print(info(f"找到 {len(mp4_files)} 个视频文件"))
    print()

    success_count = 0
    skipped_count = 0
    failed_count = 0

    for video in mp4_files:
        # 跳过已压缩的文件
        if "compressed" in video.stem.lower():
            skipped_count += 1
            continue

        if replace:
            output = video.parent / f"{video.stem}.tmp.mp4"
        else:
            output = video.parent / f"{video.stem}_compressed.mp4"

        result = _compress_video(video, output, crf, preset)

        if result is None:
            skipped_count += 1
        elif result is False:
            failed_count += 1
            print(error(f"压缩失败: {video.name}"))
        else:
            ok, orig_size, comp_size = result
            if ok:
                success_count += 1
                ratio = (1 - comp_size / orig_size) * 100
                print(
                    success(
                        f"✓ {video.name}: {format_size(orig_size)} -> {format_size(comp_size)} ({ratio:.1f}%)"
                    )
                )

                if replace:
                    video.unlink()
                    output.rename(video)
            else:
                failed_count += 1

    return success_count, skipped_count, failed_count


def compress_all(crf=32, preset="fast", replace=True):
    """
    压缩下载目录下所有用户的视频

    Args:
        crf: 压缩质量
        preset: 压缩速度
        replace: 是否替换原文件

    Returns:
        (success, skipped, failed) 计数
    """
    print_header("批量压缩视频")

    if not check_ffmpeg():
        print(error("未找到 ffmpeg"))
        print(info("请先安装 ffmpeg:"))
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt install ffmpeg")
        print("  Windows: choco install ffmpeg")
        return 0, 0, 0

    config = get_config()
    downloads_path = config.get_download_path()

    if not downloads_path.exists():
        print(error(f"下载目录不存在: {downloads_path}"))
        return 0, 0, 0

    user_dirs = [d for d in downloads_path.iterdir() if d.is_dir()]
    if not user_dirs:
        print(info("没有找到用户目录"))
        return 0, 0, 0

    print(info(f"下载目录: {downloads_path}"))
    print(info(f"找到 {len(user_dirs)} 个用户目录"))
    print()

    total_success = 0
    total_skipped = 0
    total_failed = 0

    for user_dir in sorted(user_dirs):
        success_count, skipped_count, failed_count = compress_user_dir(
            user_dir.name, crf, preset, replace
        )
        total_success += success_count
        total_skipped += skipped_count
        total_failed += failed_count
        print()

    print_header("压缩完成")
    print(success(f"成功: {total_success}"))
    print(info(f"跳过: {total_skipped}"))
    print(error(f"失败: {total_failed}"))

    return total_success, total_skipped, total_failed
