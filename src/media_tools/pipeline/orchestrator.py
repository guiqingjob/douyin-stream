"""Pipeline 流程编排器

负责串联抖音下载和 Qwen 转写流程：
下载视频(MP4) → 上传转写 → 输出文稿(md/docx)
"""

from media_tools.logger import get_logger
logger = get_logger(__name__)

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from ..transcribe.flow import run_real_flow
from ..transcribe.runtime import get_export_config, ensure_dir, now_stamp
from ..transcribe.config import load_config as load_transcribe_config
from .config import PipelineConfig, load_pipeline_config


class PipelineError(Exception):
    """Pipeline 错误"""
    pass


class PipelineResult:
    """Pipeline 执行结果"""
    def __init__(
        self,
        success: bool,
        video_path: Path,
        transcript_path: Optional[Path] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.video_path = video_path
        self.transcript_path = transcript_path
        self.error = error
    
    def __str__(self) -> str:
        if self.success:
            return f"✅ 转写成功: {self.transcript_path}"
        return f"❌ 转写失败: {self.error}"


async def transcribe_video(
    video_path: Path,
    config: Optional[PipelineConfig] = None,
    auth_state_path: Optional[Path] = None,
) -> PipelineResult:
    """对单个视频执行转写流程
    
    Args:
        video_path: 视频文件路径 (MP4)
        config: Pipeline 配置
        auth_state_path: 认证状态文件路径
    
    Returns:
        PipelineResult: 执行结果
    """
    if not video_path.exists():
        return PipelineResult(
            success=False,
            video_path=video_path,
            error=f"视频文件不存在: {video_path}"
        )
    
    if config is None:
        config = load_pipeline_config()
    
    # 确定认证路径
    if auth_state_path is None:
        transcribe_config = load_transcribe_config()
        auth_state_path = transcribe_config.paths.auth_state_path
    
    # 准备导出配置
    export_config = get_export_config(config.export_format)
    
    try:
        # 执行转写流程
        result = await run_real_flow(
            file_path=video_path,
            auth_state_path=auth_state_path,
            download_dir=config.output_dir,
            export_config=export_config,
            should_delete=config.delete_after_export,
            account_id=config.account_id,
        )
        
        # 可选：删除原视频
        if config.remove_video and not config.keep_original:
            video_path.unlink()
            logger.info(f"🗑️  已删除原视频: {video_path}")
        
        return PipelineResult(
            success=True,
            video_path=video_path,
            transcript_path=result.export_path,
        )
        
    except Exception as e:
        return PipelineResult(
            success=False,
            video_path=video_path,
            error=str(e)
        )


async def transcribe_videos_batch(
    video_paths: list[Path],
    config: Optional[PipelineConfig] = None,
    auth_state_path: Optional[Path] = None,
) -> list[PipelineResult]:
    """批量转写多个视频
    
    Args:
        video_paths: 视频文件路径列表
        config: Pipeline 配置
        auth_state_path: 认证状态文件路径
    
    Returns:
        list[PipelineResult]: 执行结果列表
    """
    if config is None:
        config = load_pipeline_config()
    
    results = []
    semaphore = asyncio.Semaphore(config.concurrency)
    
    async def _transcribe_with_semaphore(video_path: Path) -> PipelineResult:
        async with semaphore:
            return await transcribe_video(video_path, config, auth_state_path)
    
    # 并发执行
    tasks = [_transcribe_with_semaphore(path) for path in video_paths]
    results = await asyncio.gather(*tasks)
    
    return list(results)


def run_pipeline_single(
    video_path: Path,
    config: Optional[PipelineConfig] = None,
    auth_state_path: Optional[Path] = None,
) -> PipelineResult:
    """同步包装器：单个视频转写
    
    用于在同步上下文中调用异步流程
    """
    return asyncio.run(transcribe_video(video_path, config, auth_state_path))


def run_pipeline_batch(
    video_paths: list[Path],
    config: Optional[PipelineConfig] = None,
    auth_state_path: Optional[Path] = None,
) -> list[PipelineResult]:
    """同步包装器：批量转写
    
    用于在同步上下文中调用异步流程
    """
    return asyncio.run(transcribe_videos_batch(video_paths, config, auth_state_path))


def print_pipeline_summary(results: list[PipelineResult]) -> None:
    """打印 Pipeline 执行摘要"""
    total = len(results)
    success = sum(1 for r in results if r.success)
    failed = total - success
    
    logger.info("\n" + "="*50)
    logger.info(f"📊 Pipeline 执行摘要")
    logger.info("="*50)
    logger.info(f"总计: {total} | ✅ 成功: {success} | ❌ 失败: {failed}")
    logger.info("="*50)
    
    if failed > 0:
        logger.info("\n失败详情:")
        for r in results:
            if not r.success:
                logger.info(f"  - {r.video_path.name}: {r.error}")
