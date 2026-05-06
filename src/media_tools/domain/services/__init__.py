"""领域服务 - 核心业务逻辑"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from media_tools.domain.entities import Asset, AssetStatus, Creator, Task, TaskType
from media_tools.domain.repositories import (
    AssetRepository,
    CreatorRepository,
    TaskRepository,
)

logger = logging.getLogger(__name__)


class AssetDomainService:
    """素材领域服务"""
    
    def __init__(self, asset_repo: AssetRepository, creator_repo: CreatorRepository):
        self._asset_repo = asset_repo
        self._creator_repo = creator_repo
    
    def create_asset(self, creator_uid: str, title: str, **kwargs) -> Asset:
        """创建素材"""
        asset = Asset.create(creator_uid, title, **kwargs)
        self._asset_repo.save(asset)
        
        # 更新创作者统计
        creator = self._creator_repo.find_by_id(creator_uid)
        if creator:
            creator.video_count += 1
            self._creator_repo.update(creator)
        
        logger.info(f"创建素材: {asset.asset_id}")
        return asset
    
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """获取素材"""
        return self._asset_repo.find_by_id(asset_id)
    
    def list_assets(self, creator_uid: Optional[str] = None) -> List[Asset]:
        """列出素材"""
        if creator_uid:
            return self._asset_repo.find_by_creator(creator_uid)
        return self._asset_repo.find_all()
    
    def delete_asset(self, asset_id: str) -> None:
        """删除素材"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            # 更新创作者统计
            creator = self._creator_repo.find_by_id(asset.creator_uid)
            if creator:
                creator.video_count = max(0, creator.video_count - 1)
                creator.downloaded_count = max(0, creator.downloaded_count - 1)
                creator.transcript_count = max(0, creator.transcript_count - 1)
                self._creator_repo.update(creator)
            
            self._asset_repo.delete(asset_id)
            logger.info(f"删除素材: {asset_id}")
    
    def mark_downloaded(self, asset_id: str, video_path: Path) -> None:
        """标记素材已下载"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            asset.mark_downloaded(video_path)
            self._asset_repo.update(asset)
            
            # 更新创作者统计
            creator = self._creator_repo.find_by_id(asset.creator_uid)
            if creator:
                creator.increment_downloaded()
                self._creator_repo.update(creator)
            
            logger.info(f"素材已下载: {asset_id}")
    
    def mark_transcribed(self, asset_id: str, transcript_path: Path, preview: str) -> None:
        """标记素材已转写"""
        asset = self._asset_repo.find_by_id(asset_id)
        if asset:
            asset.mark_transcribed(transcript_path, preview)
            self._asset_repo.update(asset)
            
            # 更新创作者统计
            creator = self._creator_repo.find_by_id(asset.creator_uid)
            if creator:
                creator.increment_transcript()
                self._creator_repo.update(creator)
            
            logger.info(f"素材已转写: {asset_id}")


class CreatorDomainService:
    """创作者领域服务"""
    
    def __init__(self, creator_repo: CreatorRepository):
        self._creator_repo = creator_repo
    
    def create_creator(self, uid: str, nickname: str, avatar_url: Optional[str] = None) -> Creator:
        """创建创作者"""
        creator = Creator(uid=uid, nickname=nickname, avatar_url=avatar_url)
        self._creator_repo.save(creator)
        logger.info(f"创建创作者: {uid}")
        return creator
    
    def get_creator(self, uid: str) -> Optional[Creator]:
        """获取创作者"""
        return self._creator_repo.find_by_id(uid)
    
    def list_creators(self) -> List[Creator]:
        """列出所有创作者"""
        return self._creator_repo.find_all()
    
    def update_creator(self, uid: str, **kwargs) -> Optional[Creator]:
        """更新创作者信息"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            if "nickname" in kwargs:
                creator.nickname = kwargs["nickname"]
            if "avatar_url" in kwargs:
                creator.avatar_url = kwargs["avatar_url"]
            creator.update_time = datetime.now()
            self._creator_repo.update(creator)
            logger.info(f"更新创作者: {uid}")
        return creator
    
    def delete_creator(self, uid: str) -> None:
        """删除创作者"""
        self._creator_repo.delete(uid)
        logger.info(f"删除创作者: {uid}")
    
    def update_fetch_time(self, uid: str) -> None:
        """更新获取时间"""
        creator = self._creator_repo.find_by_id(uid)
        if creator:
            creator.last_fetch_time = datetime.now()
            self._creator_repo.update(creator)


class TaskDomainService:
    """任务领域服务"""
    
    def __init__(self, task_repo: TaskRepository):
        self._task_repo = task_repo
    
    def create_task(self, task_type: TaskType, payload: Dict[str, Any] = None) -> Task:
        """创建任务"""
        task = Task.create(task_type, payload=payload or {})
        self._task_repo.save(task)
        logger.info(f"创建任务: {task.task_id} ({task_type})")
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._task_repo.find_by_id(task_id)
    
    def list_tasks(self) -> List[Task]:
        """列出所有任务"""
        return self._task_repo.find_all()
    
    def list_active_tasks(self) -> List[Task]:
        """列出活跃任务"""
        return self._task_repo.find_active()
    
    def start_task(self, task_id: str) -> None:
        """开始任务"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.start()
            self._task_repo.update(task)
            logger.info(f"任务开始: {task_id}")
    
    def complete_task(self, task_id: str) -> None:
        """完成任务"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.complete()
            self._task_repo.update(task)
            logger.info(f"任务完成: {task_id}")
    
    def fail_task(self, task_id: str, error_message: str) -> None:
        """任务失败"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.fail(error_message)
            self._task_repo.update(task)
            logger.error(f"任务失败: {task_id} - {error_message}")
    
    def cancel_task(self, task_id: str) -> None:
        """取消任务"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.cancel()
            self._task_repo.update(task)
            logger.info(f"任务取消: {task_id}")
    
    def update_task_progress(self, task_id: str, progress: Dict[str, Any]) -> None:
        """更新任务进度"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.update_progress(progress)
            self._task_repo.update(task)
    
    def clear_task_history(self) -> None:
        """清空任务历史"""
        self._task_repo.clear_history()
        logger.info("清空任务历史")