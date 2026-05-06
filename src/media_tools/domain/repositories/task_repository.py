"""TaskRepository - 任务仓储接口"""
from abc import ABC, abstractmethod
from typing import List, Optional

from media_tools.domain.entities.task import Task


class TaskRepository(ABC):
    """任务仓储接口 - 定义任务数据访问抽象"""

    @abstractmethod
    def save(self, task: Task) -> None:
        """保存任务"""
        pass

    @abstractmethod
    def find_by_id(self, task_id: str) -> Optional[Task]:
        """按 ID 查询任务"""
        pass

    @abstractmethod
    def find_active(self) -> List[Task]:
        """查询活跃任务"""
        pass

    @abstractmethod
    def find_all(self) -> List[Task]:
        """查询所有任务"""
        pass

    @abstractmethod
    def find_recent(self, limit: int = 50) -> List[Task]:
        """查询最近的任务"""
        pass

    @abstractmethod
    def find_by_type(self, task_type: str) -> List[Task]:
        """按类型查询任务"""
        pass

    @abstractmethod
    def find_by_status(self, status: str) -> List[Task]:
        """按状态查询任务"""
        pass

    @abstractmethod
    def delete(self, task_id: str) -> None:
        """删除任务"""
        pass

    @abstractmethod
    def exists(self, task_id: str) -> bool:
        """检查任务是否存在"""
        pass

    @abstractmethod
    def update_progress(self, task_id: str, progress: float, msg: str) -> None:
        """更新任务进度"""
        pass

    @abstractmethod
    def clear_history(self, hours: int = 2) -> None:
        """清除历史任务"""
        pass

    @abstractmethod
    def count_by_status(self) -> dict:
        """按状态统计任务数量"""
        pass