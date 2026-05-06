"""CreatorDomainService - 创作者领域服务"""
from typing import List, Optional

from media_tools.domain.entities.creator import Creator, PlatformType, SyncStatus
from media_tools.domain.repositories import AssetRepository, CreatorRepository


class CreatorDomainService:
    """创作者领域服务 - 封装创作者相关业务逻辑"""

    def __init__(
        self,
        creator_repo: CreatorRepository,
        asset_repo: AssetRepository,
    ):
        self._creator_repo = creator_repo
        self._asset_repo = asset_repo

    def create_creator(
        self,
        uid: str,
        sec_user_id: str,
        nickname: str,
        platform: str = "douyin",
        homepage_url: Optional[str] = None,
    ) -> Creator:
        """创建创作者"""
        creator = Creator(
            uid=uid,
            sec_user_id=sec_user_id,
            nickname=nickname,
            platform=PlatformType(platform),
            homepage_url=homepage_url,
        )
        self._creator_repo.save(creator)
        return creator

    def get_creator(self, uid: str) -> Optional[Creator]:
        """获取创作者"""
        return self._creator_repo.find_by_id(uid)

    def list_creators(self, platform: Optional[str] = None) -> List[Creator]:
        """获取创作者列表"""
        if platform:
            return self._creator_repo.find_by_platform(platform)
        return self._creator_repo.find_all()

    def list_active_creators(self) -> List[Creator]:
        """获取活跃创作者列表"""
        return self._creator_repo.find_active()

    def delete_creator(self, uid: str) -> None:
        """删除创作者"""
        self._creator_repo.delete(uid)

    def update_creator_info(
        self,
        uid: str,
        nickname: Optional[str] = None,
        homepage_url: Optional[str] = None,
        avatar: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> None:
        """更新创作者信息"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            creator.update_info(nickname, homepage_url, avatar, bio)
            self._creator_repo.save(creator)

    def activate_creator(self, uid: str) -> None:
        """激活创作者"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            creator.activate()
            self._creator_repo.save(creator)

    def deactivate_creator(self, uid: str) -> None:
        """停用创作者"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            creator.deactivate()
            self._creator_repo.save(creator)

    def mark_syncing(self, uid: str) -> None:
        """标记创作者正在同步"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            creator.mark_syncing()
            self._creator_repo.save(creator)

    def update_last_fetch_time(self, uid: str) -> None:
        """更新上次同步时间"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            creator.update_last_fetch_time()
            self._creator_repo.save(creator)

    def get_creator_stats(self, uid: str) -> dict:
        """获取创作者统计信息"""
        creator = self._creator_repo.find_by_id(uid)
        if not creator:
            return {}

        asset_count = self._asset_repo.count_by_creator(uid)
        status_counts = self._asset_repo.count_by_status(uid)

        return {
            "uid": uid,
            "nickname": creator.nickname,
            "platform": creator.platform.value,
            "sync_status": creator.sync_status.value,
            "total_assets": asset_count,
            "downloaded_count": creator.downloaded_count,
            "transcript_count": creator.transcript_count,
            "status_counts": status_counts,
        }

    def refresh_creator_stats(self, uid: str) -> None:
        """刷新创作者统计数据"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            status_counts = self._asset_repo.count_by_status(uid)
            creator.downloaded_count = status_counts.get("downloaded", 0)
            creator.transcript_count = status_counts.get("completed", 0)
            self._creator_repo.save(creator)

    def exists(self, uid: str) -> bool:
        """检查创作者是否存在"""
        return self._creator_repo.exists(uid)