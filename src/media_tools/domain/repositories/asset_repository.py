"""AssetRepository - 素材仓储接口"""
from abc import ABC, abstractmethod
from typing import List, Optional

from media_tools.domain.entities.asset import Asset


class AssetRepository(ABC):
    """素材仓储接口 - 定义素材数据访问抽象"""

    @abstractmethod
    def save(self, asset: Asset) -> None:
        """保存素材"""
        pass

    @abstractmethod
    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        """按 ID 查询素材"""
        pass

    @abstractmethod
    def find_by_creator(self, creator_uid: str) -> List[Asset]:
        """按创作者查询素材"""
        pass

    @abstractmethod
    def find_all(self) -> List[Asset]:
        """查询所有素材"""
        pass

    @abstractmethod
    def find_by_status(
        self,
        video_status: Optional[str] = None,
        transcript_status: Optional[str] = None,
    ) -> List[Asset]:
        """按状态查询素材"""
        pass

    @abstractmethod
    def find_starred(self) -> List[Asset]:
        """查询收藏的素材"""
        pass

    @abstractmethod
    def find_unread(self) -> List[Asset]:
        """查询未读素材"""
        pass

    @abstractmethod
    def delete(self, asset_id: str) -> None:
        """删除素材"""
        pass

    @abstractmethod
    def exists(self, asset_id: str) -> bool:
        """检查素材是否存在"""
        pass

    @abstractmethod
    def count_by_creator(self, creator_uid: str) -> int:
        """统计创作者的素材数量"""
        pass

    @abstractmethod
    def count_by_status(self, creator_uid: Optional[str] = None) -> dict:
        """按状态统计素材数量"""
        pass