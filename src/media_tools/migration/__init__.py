"""迁移适配器 - 将旧服务层适配到新领域驱动架构"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from media_tools.domain.entities import TaskType
from media_tools.domain.services import (
    AssetDomainService,
    CreatorDomainService,
    TaskDomainService,
)
from media_tools.infrastructure.db import (
    create_asset_repository,
    create_creator_repository,
    create_task_repository,
)
from media_tools.application.pipelines import (
    VideoDownloadPipeline,
    TranscribePipeline,
    ExportPipeline,
    PipelineFactory,
)

logger = logging.getLogger(__name__)


class MigrationService:
    """迁移服务 - 适配新旧架构"""
    
    def __init__(self):
        # 旧服务实例
        self._old_services = {}
        
        # 新领域服务实例
        self._asset_service = AssetDomainService(
            create_asset_repository(),
            create_creator_repository(),
        )
        self._creator_service = CreatorDomainService(create_creator_repository())
        self._task_service = TaskDomainService(create_task_repository())
        
        # 新管道实例
        self._download_pipeline = PipelineFactory.create_download_pipeline()
        self._transcribe_pipeline = PipelineFactory.create_transcribe_pipeline()
        self._export_pipeline = PipelineFactory.create_export_pipeline()
    
    # === 资产服务迁移 ===
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """获取素材 - 新架构实现"""
        asset = self._asset_service.get_asset(asset_id)
        if asset:
            return self._asset_to_dict(asset)
        return None
    
    def list_assets(self, creator_uid: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出素材 - 新架构实现"""
        assets = self._asset_service.list_assets(creator_uid)
        return [self._asset_to_dict(asset) for asset in assets]
    
    def create_asset(self, creator_uid: str, title: str) -> Dict[str, Any]:
        """创建素材 - 新架构实现"""
        asset = self._asset_service.create_asset(creator_uid, title)
        return self._asset_to_dict(asset)
    
    def delete_asset(self, asset_id: str) -> None:
        """删除素材 - 新架构实现"""
        self._asset_service.delete_asset(asset_id)
    
    # === 创作者服务迁移 ===
    
    def get_creator(self, uid: str) -> Optional[Dict[str, Any]]:
        """获取创作者 - 新架构实现"""
        creator = self._creator_service.get_creator(uid)
        if creator:
            return self._creator_to_dict(creator)
        return None
    
    def list_creators(self) -> List[Dict[str, Any]]:
        """列出创作者 - 新架构实现"""
        creators = self._creator_service.list_creators()
        return [self._creator_to_dict(creator) for creator in creators]
    
    def create_creator(self, uid: str, nickname: str, avatar_url: Optional[str] = None) -> Dict[str, Any]:
        """创建创作者 - 新架构实现"""
        creator = self._creator_service.create_creator(uid, nickname, avatar_url)
        return self._creator_to_dict(creator)
    
    def update_creator(self, uid: str, **kwargs) -> Optional[Dict[str, Any]]:
        """更新创作者 - 新架构实现"""
        creator = self._creator_service.update_creator(uid, **kwargs)
        if creator:
            return self._creator_to_dict(creator)
        return None
    
    def delete_creator(self, uid: str) -> None:
        """删除创作者 - 新架构实现"""
        self._creator_service.delete_creator(uid)
    
    # === 任务服务迁移 ===
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务 - 新架构实现"""
        task = self._task_service.get_task(task_id)
        if task:
            return self._task_to_dict(task)
        return None
    
    def list_tasks(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """列出任务 - 新架构实现"""
        if active_only:
            tasks = self._task_service.list_active_tasks()
        else:
            tasks = self._task_service.list_tasks()
        return [self._task_to_dict(task) for task in tasks]
    
    def create_download_task(self, creator_uid: str, video_url: str, title: str) -> Dict[str, Any]:
        """创建下载任务 - 新架构实现"""
        task = self._task_service.create_task(TaskType.DOWNLOAD, {
            "creator_uid": creator_uid,
            "video_url": video_url,
            "title": title,
        })
        return self._task_to_dict(task)
    
    def create_transcribe_task(self, asset_id: str) -> Dict[str, Any]:
        """创建转写任务 - 新架构实现"""
        task = self._task_service.create_task(TaskType.TRANSCRIBE, {
            "asset_id": asset_id,
        })
        return self._task_to_dict(task)
    
    def cancel_task(self, task_id: str) -> None:
        """取消任务 - 新架构实现"""
        self._task_service.cancel_task(task_id)
    
    # === 管道执行迁移 ===
    
    async def run_download_pipeline(self, creator_uid: str, video_url: str, title: str) -> Dict[str, Any]:
        """执行下载管道 - 新架构实现"""
        context = await self._download_pipeline.run(creator_uid, video_url, title)
        return {
            "task_id": context.task_id,
            "success": not context.is_failed(),
            "errors": [str(e) for e in context.errors],
        }
    
    async def run_transcribe_pipeline(self, asset_id: str) -> Dict[str, Any]:
        """执行转写管道 - 新架构实现"""
        context = await self._transcribe_pipeline.run(asset_id)
        return {
            "task_id": context.task_id,
            "success": not context.is_failed(),
            "errors": [str(e) for e in context.errors],
        }
    
    async def run_export_pipeline(self, asset_id: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """执行导出管道 - 新架构实现"""
        from pathlib import Path
        context = await self._export_pipeline.run(asset_id, Path(output_dir) if output_dir else None)
        return {
            "task_id": context.task_id,
            "success": not context.is_failed(),
            "errors": [str(e) for e in context.errors],
        }
    
    # === 辅助方法 ===
    
    @staticmethod
    def _asset_to_dict(asset) -> Dict[str, Any]:
        """将 Asset 实体转换为字典"""
        return {
            "asset_id": asset.asset_id,
            "creator_uid": asset.creator_uid,
            "title": asset.title,
            "video_path": str(asset.video_path) if asset.video_path else None,
            "video_status": asset.video_status.value,
            "transcript_path": str(asset.transcript_path) if asset.transcript_path else None,
            "transcript_status": asset.transcript_status.value,
            "transcript_preview": asset.transcript_preview,
            "source_platform": asset.source_platform,
            "source_url": asset.source_url,
            "is_read": asset.is_read,
            "is_starred": asset.is_starred,
            "create_time": asset.create_time.isoformat(),
            "update_time": asset.update_time.isoformat(),
        }
    
    @staticmethod
    def _creator_to_dict(creator) -> Dict[str, Any]:
        """将 Creator 实体转换为字典"""
        return {
            "uid": creator.uid,
            "nickname": creator.nickname,
            "avatar_url": creator.avatar_url,
            "video_count": creator.video_count,
            "downloaded_count": creator.downloaded_count,
            "transcript_count": creator.transcript_count,
            "last_fetch_time": creator.last_fetch_time.isoformat() if creator.last_fetch_time else None,
            "status": creator.status,
            "create_time": creator.create_time.isoformat(),
            "update_time": creator.update_time.isoformat(),
        }
    
    @staticmethod
    def _task_to_dict(task) -> Dict[str, Any]:
        """将 Task 实体转换为字典"""
        return {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "payload": task.payload,
            "progress": task.progress,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }


# 全局迁移服务实例
_migration_service: Optional[MigrationService] = None


def get_migration_service() -> MigrationService:
    """获取迁移服务实例"""
    global _migration_service
    if _migration_service is None:
        _migration_service = MigrationService()
    return _migration_service


# === 兼容层 - 为旧代码提供新架构访问 ===

def get_asset_service() -> AssetDomainService:
    """兼容旧 API - 返回新架构的 AssetDomainService"""
    return AssetDomainService(
        create_asset_repository(),
        create_creator_repository(),
    )


def get_creator_service() -> CreatorDomainService:
    """兼容旧 API - 返回新架构的 CreatorDomainService"""
    return CreatorDomainService(create_creator_repository())


def get_task_service() -> TaskDomainService:
    """兼容旧 API - 返回新架构的 TaskDomainService"""
    return TaskDomainService(create_task_repository())