"""AssetDomainService - 素材领域服务"""
from pathlib import Path
from typing import List, Optional

from media_tools.domain.entities.asset import Asset, TranscriptStatus, VideoStatus
from media_tools.domain.repositories import AssetRepository, CreatorRepository


class AssetDomainService:
    """素材领域服务 - 封装素材相关业务逻辑"""

    def __init__(
        self,
        asset_repo: AssetRepository,
        creator_repo: CreatorRepository,
    ):
        self._asset_repo = asset_repo
        self._creator_repo = creator_repo

    def create_asset(
        self,
        creator_uid: str,
        title: str,
        source_url: Optional[str] = None,
        source_platform: Optional[str] = None,
    ) -> Asset:
        """创建素材"""
        import uuid

        asset = Asset(
            asset_id=str(uuid.uuid4()),
            creator_uid=creator_uid,
            title=title,
            source_url=source_url,
            source_platform=source_platform,
        )
        self._asset_repo.save(asset)
        return asset

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """获取素材"""
        return self._asset_repo.find_by_id(asset_id)

    def list_assets(self, creator_uid: Optional[str] = None) -> List[Asset]:
        """获取素材列表"""
        if creator_uid:
            return self._asset_repo.find_by_creator(creator_uid)
        return self._asset_repo.find_all()

    def delete_asset(self, asset_id: str) -> None:
        """删除素材"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            self._asset_repo.delete(asset_id)

    def mark_downloaded(self, asset_id: str, video_path: Path) -> None:
        """标记下载完成"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            asset.mark_downloaded(video_path)
            self._asset_repo.save(asset)

            creator = self._creator_repo.find_by_id(asset.creator_uid)
            if creator:
                creator.increment_downloaded()
                self._creator_repo.save(creator)

    def mark_transcribed(
        self,
        asset_id: str,
        transcript_path: Path,
        transcript_text: str,
        preview: Optional[str] = None,
    ) -> None:
        """标记转写完成"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            asset.mark_transcribed(transcript_path, transcript_text, preview)
            self._asset_repo.save(asset)

            creator = self._creator_repo.find_by_id(asset.creator_uid)
            if creator:
                creator.increment_transcript()
                self._creator_repo.save(creator)

    def mark_transcribe_failed(self, asset_id: str, error_type: str, error_message: str) -> None:
        """标记转写失败"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            asset.mark_transcribe_failed(error_type, error_message)
            self._asset_repo.save(asset)

    def mark_read(self, asset_id: str, is_read: bool) -> None:
        """标记已读状态"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            asset.mark_read(is_read)
            self._asset_repo.save(asset)

    def toggle_starred(self, asset_id: str) -> bool:
        """切换收藏状态"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            result = asset.toggle_starred()
            self._asset_repo.save(asset)
            return result
        return False

    def get_starred_assets(self) -> List[Asset]:
        """获取收藏的素材"""
        return self._asset_repo.find_starred()

    def get_unread_assets(self) -> List[Asset]:
        """获取未读素材"""
        return self._asset_repo.find_unread()

    def get_assets_by_status(
        self,
        video_status: Optional[str] = None,
        transcript_status: Optional[str] = None,
    ) -> List[Asset]:
        """按状态查询素材"""
        return self._asset_repo.find_by_status(video_status, transcript_status)

    def get_downloaded_assets(self) -> List[Asset]:
        """获取已下载的素材"""
        return self._asset_repo.find_by_status(video_status=VideoStatus.DOWNLOADED.value)

    def get_need_transcript_assets(self) -> List[Asset]:
        """获取需要转写的素材（已下载但未转写）"""
        return self._asset_repo.find_by_status(
            video_status=VideoStatus.DOWNLOADED.value,
            transcript_status=TranscriptStatus.NONE.value,
        )

    def count_assets_by_creator(self, creator_uid: str) -> int:
        """统计创作者的素材数量"""
        return self._asset_repo.count_by_creator(creator_uid)

    def count_assets_by_status(self, creator_uid: Optional[str] = None) -> dict:
        """按状态统计素材数量"""
        return self._asset_repo.count_by_status(creator_uid)