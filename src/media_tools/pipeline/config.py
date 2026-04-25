"""Pipeline 配置管理 — 委托给统一配置系统。"""
from __future__ import annotations

from media_tools.core.config import get_pipeline_config, PipelineConfig

__all__ = ["PipelineConfig", "load_pipeline_config"]


def load_pipeline_config() -> PipelineConfig:
    """加载 Pipeline 配置（从环境变量）。"""
    return get_pipeline_config()
