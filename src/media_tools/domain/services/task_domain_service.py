"""TaskDomainService - 任务领域服务"""
from typing import Any, List, Optional

from media_tools.domain.entities.task import Task, TaskStatus, TaskType
from media_tools.domain.repositories import TaskRepository


class TaskDomainService:
    """任务领域服务 - 封装任务相关业务逻辑"""

    def __init__(self, task_repo: TaskRepository):
        self._task_repo = task_repo

    def create_task(self, task_id: str, task_type: str, payload: Optional[dict] = None) -> Task:
        """创建任务"""
        task = Task(
            task_id=task_id,
            task_type=TaskType(task_type),
            payload=payload,
        )
        self._task_repo.save(task)
        return task

    def create_running_task(self, task_id: str, task_type: str, payload: Optional[dict] = None) -> Task:
        """创建并标记为运行中的任务"""
        task = Task(
            task_id=task_id,
            task_type=TaskType(task_type),
            status=TaskStatus.RUNNING,
            payload=payload,
        )
        self._task_repo.save(task)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._task_repo.find_by_id(task_id)

    def list_tasks(self) -> List[Task]:
        """获取所有任务"""
        return self._task_repo.find_all()

    def list_active_tasks(self) -> List[Task]:
        """获取活跃任务"""
        return self._task_repo.find_active()

    def list_recent_tasks(self, limit: int = 50) -> List[Task]:
        """获取最近的任务"""
        return self._task_repo.find_recent(limit)

    def start_task(self, task_id: str) -> None:
        """启动任务"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.start()
            self._task_repo.save(task)

    def complete_task(self, task_id: str) -> None:
        """完成任务"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.complete()
            self._task_repo.save(task)

    def fail_task(self, task_id: str, error_msg: str) -> None:
        """标记任务失败"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.fail(error_msg)
            self._task_repo.save(task)

    def cancel_task(self, task_id: str) -> None:
        """取消任务"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.cancel()
            self._task_repo.save(task)

    def mark_partial_failed(self, task_id: str) -> None:
        """标记任务部分失败"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.mark_partial_failed()
            self._task_repo.save(task)

    def update_task_progress(self, task_id: str, progress: float, msg: str) -> None:
        """更新任务进度"""
        task = self._task_repo.find_by_id(task_id)
        if task and not task.is_terminal():
            task.update_progress(progress, msg)
            self._task_repo.save(task)

    def update_task_payload(self, task_id: str, key: str, value: Any) -> None:
        """更新任务 payload"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.update_payload(key, value)
            self._task_repo.save(task)

    def patch_task_payload(self, task_id: str, patch: dict[str, Any]) -> None:
        """批量更新任务 payload"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.patch_payload(patch)
            self._task_repo.save(task)

    def request_task_cancel(self, task_id: str) -> None:
        """请求取消任务"""
        task = self._task_repo.find_by_id(task_id)
        if task:
            task.request_cancel()
            self._task_repo.save(task)

    def delete_task(self, task_id: str) -> None:
        """删除任务"""
        self._task_repo.delete(task_id)

    def clear_task_history(self, hours: int = 2) -> None:
        """清除历史任务"""
        self._task_repo.clear_history(hours)

    def get_task_count_by_status(self) -> dict:
        """按状态统计任务数量"""
        return self._task_repo.count_by_status()

    def is_task_active(self, task_id: str) -> bool:
        """检查任务是否活跃"""
        task = self._task_repo.find_by_id(task_id)
        return task.is_active() if task else False