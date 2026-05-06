"""TranscriptRepository - 转写仓储接口"""
from abc import ABC, abstractmethod
from typing import List, Optional

from media_tools.domain.entities.transcript import Transcript


class TranscriptRepository(ABC):
    """转写仓储接口 - 定义转写数据访问抽象"""

    @abstractmethod
    def save(self, transcript: Transcript) -> None:
        """保存转写"""
        pass

    @abstractmethod
    def find_by_id(self, transcript_id: str) -> Optional[Transcript]:
        """按 ID 查询转写"""
        pass

    @abstractmethod
    def find_by_asset(self, asset_id: str) -> Optional[Transcript]:
        """按素材 ID 查询转写"""
        pass

    @abstractmethod
    def find_all(self) -> List[Transcript]:
        """查询所有转写"""
        pass

    @abstractmethod
    def delete(self, transcript_id: str) -> None:
        """删除转写"""
        pass

    @abstractmethod
    def exists(self, asset_id: str) -> bool:
        """检查素材是否已有转写"""
        pass

    @abstractmethod
    def update_preview(self, transcript_id: str, preview: str) -> None:
        """更新转写预览"""
        pass