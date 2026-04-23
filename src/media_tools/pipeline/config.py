"""Pipeline 配置管理"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from media_tools.douyin.core.config_mgr import get_config

@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Pipeline 流程配置"""
    # 转写设置
    export_format: str = "md"  # md 或 docx
    output_dir: str = ""  # 空字符串表示延迟初始化，由 load_pipeline_config() 或 output_path property 设置
    delete_after_export: bool = True  # 默认为 True：导出后立即删除云端记录以节省额度
    account_id: str = ""

    # 清理设置
    remove_video: bool = False
    keep_original: bool = True

    # 并发设置
    concurrency: int = 5

    @property
    def output_path(self) -> Path:
        if self.output_dir:
            return Path(self.output_dir).resolve()
        return get_config().project_root / "transcripts"


def _safe_int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def load_pipeline_config() -> PipelineConfig:
    """从环境变量或默认值加载配置"""
    return PipelineConfig(
        export_format=os.environ.get("PIPELINE_EXPORT_FORMAT", "md").strip().lower(),
        output_dir=os.environ.get("PIPELINE_OUTPUT_DIR", str(get_config().project_root / "transcripts")).strip(),
        delete_after_export=os.environ.get("PIPELINE_DELETE_AFTER_EXPORT", "true").lower() == "true",
        account_id=os.environ.get("PIPELINE_ACCOUNT_ID", "").strip(),
        remove_video=os.environ.get("PIPELINE_REMOVE_VIDEO", "false").lower() == "true",
        keep_original=os.environ.get("PIPELINE_KEEP_ORIGINAL", "true").lower() == "true",
        concurrency=_safe_int_env("PIPELINE_CONCURRENCY", 5),
    )
