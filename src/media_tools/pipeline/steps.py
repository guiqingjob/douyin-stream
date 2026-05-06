"""Pipeline 步骤实现 - 基于接口的具体步骤类"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .interface import (
    PipelineContext,
    PipelineStep,
    VideoDownloadStep,
    AudioExtractStep,
    TranscribeStep,
    ExportStep,
    CleanupStep,
)

logger = logging.getLogger(__name__)


class F2VideoDownloadStep(VideoDownloadStep):
    """基于 F2 SDK 的视频下载步骤"""
    
    def __init__(self, url: str):
        self._url = url
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """下载视频文件"""
        from media_tools.douyin.core.structured_downloader import get_structured_downloader
        
        logger.info(f"开始下载视频: {self._url}")
        
        try:
            downloader = get_structured_downloader()
            downloaded, skipped = await downloader.download_by_url(self._url)
            
            if downloaded > 0:
                # 假设下载成功后获取文件路径
                # 实际实现需要从下载器获取结果
                context.status = "downloaded"
                logger.info("视频下载成功")
            else:
                context.status = "skipped"
                logger.info("视频已存在，跳过下载")
                
        except Exception as e:
            logger.error(f"视频下载失败: {e}")
            context.add_error(e)
            context.status = "failed"
        
        return context


class FFmpegAudioExtractStep(AudioExtractStep):
    """基于 FFmpeg 的音频提取步骤"""
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """从视频中提取音频"""
        if not context.video_path:
            logger.warning("没有视频文件，跳过音频提取")
            return context
        
        logger.info(f"开始提取音频: {context.video_path}")
        
        try:
            # 构建输出路径
            audio_path = context.video_path.with_suffix(".wav")
            
            # 使用 FFmpeg 提取音频
            cmd = [
                "ffmpeg",
                "-i", str(context.video_path),
                "-vn",  # 禁用视频流
                "-acodec", "pcm_s16le",  # PCM 16位小端
                "-ar", "16000",  # 采样率 16kHz
                "-ac", "1",  # 单声道
                "-y",  # 覆盖输出文件
                str(audio_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg 执行失败: {stderr.decode('utf-8')}")
            
            context.audio_path = audio_path
            context.status = "audio_extracted"
            logger.info(f"音频提取成功: {audio_path}")
            
        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            context.add_error(e)
            context.status = "failed"
        
        return context


class QwenTranscribeStep(TranscribeStep):
    """基于 Qwen API 的转写步骤"""
    
    def __init__(self, account_id: Optional[str] = None):
        self._account_id = account_id
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """调用 Qwen API 转写音频"""
        if not context.audio_path:
            logger.warning("没有音频文件，跳过转写")
            return context
        
        logger.info(f"开始转写音频: {context.audio_path}")
        
        try:
            from media_tools.transcribe.flow import run_real_flow
            
            # 调用现有的转写流程
            result = await run_real_flow(
                audio_path=str(context.audio_path),
                account_id=self._account_id,
            )
            
            # 解析结果
            if result.get("success"):
                context.transcript_path = Path(result.get("output_path", ""))
                context.metadata["transcript"] = result.get("transcript", "")
                context.status = "transcribed"
                logger.info("转写成功")
            else:
                raise RuntimeError(result.get("error", "转写失败"))
                
        except Exception as e:
            logger.error(f"转写失败: {e}")
            context.add_error(e)
            context.status = "failed"
        
        return context


class MarkdownExportStep(ExportStep):
    """Markdown 导出步骤"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self._output_dir = output_dir
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """导出为 Markdown 文件"""
        if not context.transcript_path:
            logger.warning("没有转写结果，跳过导出")
            return context
        
        logger.info(f"开始导出 Markdown: {context.transcript_path}")
        
        try:
            # 如果没有指定输出目录，使用转写文件所在目录
            output_dir = self._output_dir or context.transcript_path.parent
            
            # 读取转写内容
            content = context.transcript_path.read_text(encoding="utf-8")
            
            # 创建 Markdown 文件
            md_filename = context.transcript_path.stem + ".md"
            md_path = output_dir / md_filename
            
            # 添加标题
            title = context.metadata.get("title", "视频转写")
            md_content = f"# {title}\n\n{content}"
            
            md_path.write_text(md_content, encoding="utf-8")
            
            context.set_result("export_path", str(md_path))
            context.status = "exported"
            logger.info(f"导出成功: {md_path}")
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            context.add_error(e)
            context.status = "failed"
        
        return context


class LocalCleanupStep(CleanupStep):
    """本地文件清理步骤"""
    
    def __init__(self, keep_audio: bool = False):
        self._keep_audio = keep_audio
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """清理临时文件"""
        logger.info("开始清理临时文件")
        
        try:
            # 删除音频文件（如果不需要保留）
            if context.audio_path and not self._keep_audio:
                context.audio_path.unlink(missing_ok=True)
                logger.info(f"已删除音频文件: {context.audio_path}")
            
            # 可以添加更多清理逻辑
            
            context.status = "cleaned"
            logger.info("清理完成")
            
        except Exception as e:
            logger.error(f"清理失败: {e}")
            context.add_error(e)
            
        return context


# 步骤工厂类
class PipelineStepFactory:
    """管道步骤工厂"""
    
    @staticmethod
    def create_download_step(url: str) -> F2VideoDownloadStep:
        return F2VideoDownloadStep(url)
    
    @staticmethod
    def create_audio_extract_step() -> FFmpegAudioExtractStep:
        return FFmpegAudioExtractStep()
    
    @staticmethod
    def create_transcribe_step(account_id: Optional[str] = None) -> QwenTranscribeStep:
        return QwenTranscribeStep(account_id)
    
    @staticmethod
    def create_export_step(output_dir: Optional[Path] = None) -> MarkdownExportStep:
        return MarkdownExportStep(output_dir)
    
    @staticmethod
    def create_cleanup_step(keep_audio: bool = False) -> LocalCleanupStep:
        return LocalCleanupStep(keep_audio)