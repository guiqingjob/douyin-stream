from __future__ import annotations
"""Pipeline 管道流程接口定义 - 定义可插拔的管道步骤"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class PipelineContext:
    """管道执行上下文 - 传递状态和数据"""
    
    def __init__(self):
        self.video_path: Optional[Path] = None
        self.audio_path: Optional[Path] = None
        self.transcript_path: Optional[Path] = None
        self.metadata: Dict[str, Any] = {}
        self.status: str = "pending"
        self.errors: List[Exception] = []
        self.step_results: Dict[str, Any] = {}
    
    def set_result(self, step_name: str, result: Any) -> None:
        """记录步骤执行结果"""
        self.step_results[step_name] = result
    
    def get_result(self, step_name: str) -> Any:
        """获取步骤执行结果"""
        return self.step_results.get(step_name)
    
    def add_error(self, error: Exception) -> None:
        """添加错误信息"""
        self.errors.append(error)
    
    def is_failed(self) -> bool:
        """判断是否失败"""
        return len(self.errors) > 0 or self.status == "failed"


class PipelineStep(ABC):
    """管道步骤抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """步骤名称"""
        pass
    
    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """执行步骤，返回更新后的上下文"""
        pass
    
    def can_execute(self, context: PipelineContext) -> bool:
        """判断是否可以执行此步骤（默认总是可以执行）"""
        return not context.is_failed()
    
    async def cleanup(self, context: PipelineContext) -> None:
        """清理资源（可选）"""
        pass


class Pipeline:
    """管道执行器 - 协调多个步骤的执行"""
    
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps
    
    async def run(self, context: PipelineContext) -> PipelineContext:
        """按顺序执行所有步骤"""
        for step in self.steps:
            if not step.can_execute(context):
                logger.info(f"跳过步骤 {step.name} (上下文状态不允许)")
                continue
            
            logger.info(f"开始执行步骤: {step.name}")
            try:
                context = await step.execute(context)
                logger.info(f"步骤 {step.name} 执行完成")
            except Exception as e:
                logger.error(f"步骤 {step.name} 执行失败: {e}")
                context.add_error(e)
                context.status = "failed"
                break
        
        if not context.is_failed():
            context.status = "completed"
        
        return context


class PipelineStepFactory(ABC):
    """步骤工厂接口 - 创建步骤实例"""
    
    @abstractmethod
    def create(self, **kwargs) -> PipelineStep:
        """创建步骤实例"""
        pass


# 具体步骤类型定义

class VideoDownloadStep(PipelineStep):
    """视频下载步骤"""
    
    @property
    def name(self) -> str:
        return "video_download"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """下载视频"""
        # 实现待完成
        return context


class AudioExtractStep(PipelineStep):
    """音频提取步骤"""
    
    @property
    def name(self) -> str:
        return "audio_extract"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """从视频中提取音频"""
        # 实现待完成
        return context


class TranscribeStep(PipelineStep):
    """转写步骤"""
    
    @property
    def name(self) -> str:
        return "transcribe"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """调用 Qwen API 转写音频"""
        # 实现待完成
        return context


class ExportStep(PipelineStep):
    """导出步骤"""
    
    @property
    def name(self) -> str:
        return "export"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """导出为 Markdown 文件"""
        # 实现待完成
        return context


class CleanupStep(PipelineStep):
    """清理步骤"""
    
    @property
    def name(self) -> str:
        return "cleanup"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """清理临时文件"""
        # 实现待完成
        return context


# 日志记录器
import logging
logger = logging.getLogger(__name__)