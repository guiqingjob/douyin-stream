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

# 导入日志记录器
from ..utils.logger import logger


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
        (success, original_size, compressed_size, error_msg)
        - success: bool
        - original_size: int (字节)
        - compressed_size: int (字节)
        - error_msg: str 或 None
    """
    info_data = _get_video_info(input_path)
    if not info_data:
        return (False, 0, 0, "无法获取视频信息")

    original_size = info_data["size"]
    height = info_data.get("height", 0)

    # 跳过小文件（< 5MB）
    if original_size < 5 * 1024 * 1024:
        return (False, original_size, 0, "文件小于5MB，跳过压缩")

    # 跳过低分辨率（< 720p）
    if height > 0 and height < 720:
        return (False, original_size, 0, "分辨率低于720p，跳过压缩")

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
        error_msg = f"FFmpeg错误: {result.stderr[:200]}" if result.stderr else "FFmpeg执行失败"
        if output_path.exists():
            output_path.unlink()
        return (False, original_size, 0, error_msg)

    compressed_info = _get_video_info(output_path)
    if compressed_info is None:
        if output_path.exists():
            output_path.unlink()
        return (False, original_size, 0, "无法获取压缩后视频信息")
    
    compressed_size = compressed_info.get("size", 0)

    if compressed_size == 0:
        if output_path.exists():
            output_path.unlink()
        return (False, original_size, 0, "压缩后文件为空")

    return (True, original_size, compressed_size, None)


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
    
    # 防止路径遍历攻击
    user_folder = Path(user_folder).name  # 只取文件名，忽略路径
    user_dir = downloads_path / user_folder
    
    # 验证最终路径确实在downloads_path下
    try:
        user_dir.resolve().relative_to(downloads_path.resolve())
    except ValueError:
        logger.info(error(f"非法目录: {user_folder}"))
        return 0, 0, 0

    if not user_dir.exists():
        logger.info(error(f"目录不存在: {user_dir}"))
        return 0, 0, 0

    mp4_files = list(user_dir.glob("*.mp4"))
    if not mp4_files:
        logger.info(info(f"没有找到视频文件: {user_dir}"))
        return 0, 0, 0

    logger.info(info(f"处理用户目录: {user_folder}"))
    logger.info(info(f"找到 {len(mp4_files)} 个视频文件"))
    logger.info()

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

        success, orig_size, comp_size, error_msg = result
        
        if success:
            # 压缩成功，替换原文件
            if replace:
                try:
                    output.replace(video)
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.info(error(f"替换文件失败: {video.name} - {e}"))
                    if output.exists():
                        output.unlink()
            else:
                success_count += 1
                logger.info(success(f"压缩成功: {video.name} ({orig_size/1024/1024:.1f}MB -> {comp_size/1024/1024:.1f}MB)"))
        elif error_msg and ("跳过" in error_msg or "小于" in error_msg or "低于" in error_msg):
            # 主动跳过
            skipped_count += 1
        else:
            # 压缩失败
            failed_count += 1
            logger.info(error(f"压缩失败: {video.name} - {error_msg}"))
            if output.exists():
                output.unlink()

    logger.info()
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
        logger.info(error("未找到 ffmpeg"))
        logger.info(info("请先安装 ffmpeg:"))
        logger.info("  macOS:   brew install ffmpeg")
        logger.info("  Ubuntu:  sudo apt install ffmpeg")
        logger.info("  Windows: choco install ffmpeg")
        return 0, 0, 0

    config = get_config()
    downloads_path = config.get_download_path()

    if not downloads_path.exists():
        logger.info(error(f"下载目录不存在: {downloads_path}"))
        return 0, 0, 0

    user_dirs = [d for d in downloads_path.iterdir() if d.is_dir()]
    if not user_dirs:
        logger.info(info("没有找到用户目录"))
        return 0, 0, 0

    logger.info(info(f"下载目录: {downloads_path}"))
    logger.info(info(f"找到 {len(user_dirs)} 个用户目录"))
    logger.info()

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
        logger.info()

    print_header("压缩完成")
    logger.info(success(f"成功: {total_success}"))
    logger.info(info(f"跳过: {total_skipped}"))
    logger.info(error(f"失败: {total_failed}"))

    return total_success, total_skipped, total_failed
