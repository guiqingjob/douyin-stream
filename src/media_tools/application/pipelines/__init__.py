from __future__ import annotations
"""应用层 - 业务管道编排"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from media_tools.domain.entities import Asset, Task, TaskType
from media_tools.domain.services import AssetDomainService, TaskDomainService
from media_tools.infrastructure.db import (
    create_asset_repository,
    create_creator_repository,
    create_task_repository,
)

logger = logging.getLogger(__name__)


class PipelineContext:
    """管道执行上下文"""
    
    def __init__(self):
        self.task_id: Optional[str] = None
        self.asset: Optional[Asset] = None
        self.video_path: Optional[Path] = None
        self.audio_path: Optional[Path] = None
        self.transcript_content: Optional[str] = None
        self.export_path: Optional[Path] = None
        self.errors: list = []
    
    def add_error(self, error: Exception) -> None:
        """添加错误"""
        self.errors.append(error)
    
    def is_failed(self) -> bool:
        """是否失败"""
        return len(self.errors) > 0


class VideoDownloadPipeline:
    """视频下载管道"""
    
    def __init__(self):
        self._asset_service = AssetDomainService(
            create_asset_repository(),
            create_creator_repository(),
        )
        self._task_service = TaskDomainService(create_task_repository())
    
    async def run(self, creator_uid: str, video_url: str, title: str) -> PipelineContext:
        """执行下载管道"""
        context = PipelineContext()
        
        # 创建任务
        task = self._task_service.create_task(TaskType.DOWNLOAD, {
            "creator_uid": creator_uid,
            "video_url": video_url,
            "title": title,
        })
        context.task_id = task.task_id
        self._task_service.start_task(task.task_id)
        
        try:
            # 下载视频
            await self._download_video(context, creator_uid, video_url, title)
            
            # 标记完成
            self._task_service.complete_task(task.task_id)
            
        except Exception as e:
            context.add_error(e)
            self._task_service.fail_task(task.task_id, str(e))
        
        return context
    
    async def _download_video(self, context: PipelineContext, creator_uid: str, video_url: str, title: str) -> None:
        """下载视频"""
        # 创建素材
        asset = self._asset_service.create_asset(creator_uid, title)
        context.asset = asset
        
        # 模拟下载（实际调用下载器）
        from media_tools.douyin.core.structured_downloader import get_structured_downloader
        
        downloader = get_structured_downloader()
        downloaded, skipped = await downloader.download_by_url(video_url)
        
        if downloaded > 0:
            # 获取下载路径
            video_path = self._get_video_path(creator_uid, title, asset.asset_id)
            context.video_path = video_path
            self._asset_service.mark_downloaded(asset.asset_id, video_path)
            logger.info(f"视频下载成功: {video_path}")
        elif skipped > 0:
            logger.info(f"视频已存在，跳过下载")
    
    def _get_video_path(self, creator_uid: str, title: str, asset_id: str) -> Path:
        """获取视频路径"""
        from media_tools.common.paths import get_download_path
        import re
        
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)[:50]
        return get_download_path() / creator_uid / f"{safe_title}_{asset_id}.mp4"


class TranscribePipeline:
    """转写管道"""
    
    def __init__(self):
        self._asset_service = AssetDomainService(
            create_asset_repository(),
            create_creator_repository(),
        )
        self._task_service = TaskDomainService(create_task_repository())
    
    async def run(self, asset_id: str) -> PipelineContext:
        """执行转写管道"""
        context = PipelineContext()
        
        # 创建任务
        task = self._task_service.create_task(TaskType.TRANSCRIBE, {
            "asset_id": asset_id,
        })
        context.task_id = task.task_id
        self._task_service.start_task(task.task_id)
        
        try:
            # 获取素材
            asset = self._asset_service.get_asset(asset_id)
            if not asset:
                raise ValueError(f"素材不存在: {asset_id}")
            context.asset = asset
            
            # 转写
            await self._transcribe_audio(context)
            
            # 标记完成
            self._task_service.complete_task(task.task_id)
            
        except Exception as e:
            context.add_error(e)
            self._task_service.fail_task(task.task_id, str(e))
        
        return context
    
    async def _transcribe_audio(self, context: PipelineContext) -> None:
        """转写音频"""
        if not context.asset or not context.asset.video_path:
            raise ValueError("没有视频文件")
        
        # 调用转写服务
        from media_tools.transcribe.flow import run_real_flow
        
        result = await run_real_flow(
            audio_path=str(context.asset.video_path),
        )
        
        if result.get("success"):
            context.transcript_content = result.get("transcript", "")
            transcript_path = Path(result.get("output_path", ""))
            preview = context.transcript_content[:200] + "..." if len(context.transcript_content) > 200 else context.transcript_content
            
            self._asset_service.mark_transcribed(
                context.asset.asset_id,
                transcript_path,
                preview,
            )
            logger.info(f"转写成功: {context.asset.asset_id}")


class ExportPipeline:
    """导出管道"""
    
    def __init__(self):
        self._asset_service = AssetDomainService(
            create_asset_repository(),
            create_creator_repository(),
        )
        self._task_service = TaskDomainService(create_task_repository())
    
    async def run(self, asset_id: str, output_dir: Optional[Path] = None) -> PipelineContext:
        """执行导出管道"""
        context = PipelineContext()
        
        # 创建任务
        task = self._task_service.create_task(TaskType.EXPORT, {
            "asset_id": asset_id,
            "output_dir": str(output_dir) if output_dir else "",
        })
        context.task_id = task.task_id
        self._task_service.start_task(task.task_id)
        
        try:
            # 获取素材
            asset = self._asset_service.get_asset(asset_id)
            if not asset:
                raise ValueError(f"素材不存在: {asset_id}")
            context.asset = asset
            
            # 导出
            await self._export_transcript(context, output_dir)
            
            # 标记完成
            self._task_service.complete_task(task.task_id)
            
        except Exception as e:
            context.add_error(e)
            self._task_service.fail_task(task.task_id, str(e))
        
        return context
    
    async def _export_transcript(self, context: PipelineContext, output_dir: Optional[Path]) -> None:
        """导出转写内容"""
        if not context.asset or not context.asset.transcript_path:
            raise ValueError("没有转写内容")
        
        if not output_dir:
            output_dir = context.asset.transcript_path.parent
        
        # 读取转写内容
        content = context.asset.transcript_path.read_text(encoding="utf-8")
        
        # 创建 Markdown 文件
        md_path = output_dir / f"{context.asset.title}.md"
        md_content = f"# {context.asset.title}\n\n{content}"
        md_path.write_text(md_content, encoding="utf-8")
        
        context.export_path = md_path
        logger.info(f"导出成功: {md_path}")


class PipelineFactory:
    """管道工厂"""
    
    @staticmethod
    def create_download_pipeline() -> VideoDownloadPipeline:
        return VideoDownloadPipeline()
    
    @staticmethod
    def create_transcribe_pipeline() -> TranscribePipeline:
        return TranscribePipeline()
    
    @staticmethod
    def create_export_pipeline() -> ExportPipeline:
        return ExportPipeline()