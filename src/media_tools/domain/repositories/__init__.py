"""仓储接口 - 定义数据访问抽象"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from media_tools.domain.entities import Asset, Creator, Task, Transcript


class AssetRepository(ABC):
    """素材仓储接口"""
    
    @abstractmethod
    def save(self, asset: Asset) -> None:
        """保存素材"""
        pass
    
    @abstractmethod
    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        """根据ID查找素材"""
        pass
    
    @abstractmethod
    def find_by_creator(self, creator_uid: str) -> List[Asset]:
        """根据创作者ID查找素材"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Asset]:
        """查找所有素材"""
        pass
    
    @abstractmethod
    def delete(self, asset_id: str) -> None:
        """删除素材"""
        pass
    
    @abstractmethod
    def update(self, asset: Asset) -> None:
        """更新素材"""
        pass
    
    @abstractmethod
    def count_by_status(self, status: str) -> int:
        """按状态统计素材数量"""
        pass


class CreatorRepository(ABC):
    """创作者仓储接口"""
    
    @abstractmethod
    def save(self, creator: Creator) -> None:
        """保存创作者"""
        pass
    
    @abstractmethod
    def find_by_id(self, uid: str) -> Optional[Creator]:
        """根据ID查找创作者"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Creator]:
        """查找所有创作者"""
        pass
    
    @abstractmethod
    def delete(self, uid: str) -> None:
        """删除创作者"""
        pass
    
    @abstractmethod
    def update(self, creator: Creator) -> None:
        """更新创作者"""
        pass


class TaskRepository(ABC):
    """任务仓储接口"""
    
    @abstractmethod
    def save(self, task: Task) -> None:
        """保存任务"""
        pass
    
    @abstractmethod
    def find_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID查找任务"""
        pass
    
    @abstractmethod
    def find_active(self) -> List[Task]:
        """查找活跃任务"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Task]:
        """查找所有任务"""
        pass
    
    @abstractmethod
    def update(self, task: Task) -> None:
        """更新任务"""
        pass
    
    @abstractmethod
    def delete(self, task_id: str) -> None:
        """删除任务"""
        pass
    
    @abstractmethod
    def clear_history(self) -> None:
        """清空历史任务"""
        pass


class TranscriptRepository(ABC):
    """转写仓储接口"""
    
    @abstractmethod
    def save(self, transcript: Transcript) -> None:
        """保存转写"""
        pass
    
    @abstractmethod
    def find_by_id(self, transcript_id: str) -> Optional[Transcript]:
        """根据ID查找转写"""
        pass
    
    @abstractmethod
    def find_by_asset(self, asset_id: str) -> Optional[Transcript]:
        """根据素材ID查找转写"""
        pass
    
    @abstractmethod
    def delete(self, transcript_id: str) -> None:
        """删除转写"""
        pass