"""迁移适配层 - 桥接新旧架构"""
from typing import Optional

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


# 迁移服务工厂（兼容旧代码）
def get_migration_service():
    """兼容旧代码的迁移服务工厂"""
    return AssetDomainService(
        asset_repo=create_asset_repository(),
        creator_repo=create_creator_repository(),
    )


def migrate_asset_service() -> AssetDomainService:
    """迁移适配：创建 AssetDomainService 实例"""
    return AssetDomainService(
        asset_repo=create_asset_repository(),
        creator_repo=create_creator_repository(),
    )


def migrate_creator_service() -> CreatorDomainService:
    """迁移适配：创建 CreatorDomainService 实例"""
    return CreatorDomainService(
        creator_repo=create_creator_repository(),
        asset_repo=create_asset_repository(),
    )


def migrate_task_service() -> TaskDomainService:
    """迁移适配：创建 TaskDomainService 实例"""
    return TaskDomainService(
        task_repo=create_task_repository(),
    )


# 全局服务实例（保持向后兼容）
_asset_service: Optional[AssetDomainService] = None
_creator_service: Optional[CreatorDomainService] = None
_task_service: Optional[TaskDomainService] = None


def get_asset_service() -> AssetDomainService:
    """获取全局 AssetDomainService 实例"""
    global _asset_service
    if _asset_service is None:
        _asset_service = migrate_asset_service()
    return _asset_service


def get_creator_service() -> CreatorDomainService:
    """获取全局 CreatorDomainService 实例"""
    global _creator_service
    if _creator_service is None:
        _creator_service = migrate_creator_service()
    return _creator_service


def get_task_service() -> TaskDomainService:
    """获取全局 TaskDomainService 实例"""
    global _task_service
    if _task_service is None:
        _task_service = migrate_task_service()
    return _task_service