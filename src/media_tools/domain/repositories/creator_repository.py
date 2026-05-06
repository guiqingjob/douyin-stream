"""CreatorRepository - 创作者仓储接口"""
from abc import ABC, abstractmethod
from typing import List, Optional

from media_tools.domain.entities.creator import Creator


class CreatorRepository(ABC):
    """创作者仓储接口 - 定义创作者数据访问抽象"""

    @abstractmethod
    def save(self, creator: Creator) -> None:
        """保存创作者"""
        pass

    @abstractmethod
    def find_by_id(self, uid: str) -> Optional[Creator]:
        """按 ID 查询创作者"""
        pass

    @abstractmethod
    def find_all(self) -> List[Creator]:
        """查询所有创作者"""
        pass

    @abstractmethod
    def find_by_platform(self, platform: str) -> List[Creator]:
        """按平台查询创作者"""
        pass

    @abstractmethod
    def find_active(self) -> List[Creator]:
        """查询活跃的创作者"""
        pass

    @abstractmethod
    def delete(self, uid: str) -> None:
        """删除创作者"""
        pass

    @abstractmethod
    def exists(self, uid: str) -> bool:
        """检查创作者是否存在"""
        pass

    @abstractmethod
    def update_downloaded_count(self, uid: str, count: int) -> None:
        """更新下载计数"""
        pass

    @abstractmethod
    def update_transcript_count(self, uid: str, count: int) -> None:
        """更新转写计数"""
        pass