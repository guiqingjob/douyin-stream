"""仓储接口模块 - 定义数据访问抽象"""
from .asset_repository import AssetRepository
from .creator_repository import CreatorRepository
from .task_repository import TaskRepository
from .transcript_repository import TranscriptRepository

__all__ = ["AssetRepository", "CreatorRepository", "TaskRepository", "TranscriptRepository"]