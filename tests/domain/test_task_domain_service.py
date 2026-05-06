"""领域服务单元测试 - TaskDomainService"""
import pytest
from unittest.mock import Mock

from media_tools.domain.entities import Task, TaskType, TaskStatus
from media_tools.domain.services import TaskDomainService


class TestTaskDomainService:
    """任务领域服务测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_task_repo = Mock()
        self.service = TaskDomainService(self.mock_task_repo)

    def test_create_task(self):
        """测试创建任务"""
        task = self.service.create_task("task1", "download", {"url": "http://video.mp4"})
        
        assert task.task_id == "task1"
        assert task.task_type == TaskType.DOWNLOAD
        assert task.status == TaskStatus.PENDING
        assert task.payload == {"url": "http://video.mp4"}
        
        self.mock_task_repo.save.assert_called_once()

    def test_create_task_without_payload(self):
        """测试创建任务（不带payload）"""
        task = self.service.create_task("task1", "transcribe")
        
        assert task.payload == {}
        self.mock_task_repo.save.assert_called_once()

    def test_get_task(self):
        """测试获取任务"""
        mock_task = Task(task_id="task1", task_type=TaskType.DOWNLOAD)
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        result = self.service.get_task("task1")
        
        assert result == mock_task
        self.mock_task_repo.find_by_id.assert_called_once_with("task1")

    def test_get_task_not_found(self):
        """测试获取不存在的任务"""
        self.mock_task_repo.find_by_id.return_value = None
        
        result = self.service.get_task("task1")
        
        assert result is None

    def test_list_tasks(self):
        """测试列出所有任务"""
        mock_tasks = [
            Task(task_id="task1", task_type=TaskType.DOWNLOAD),
            Task(task_id="task2", task_type=TaskType.TRANSCRIBE),
        ]
        self.mock_task_repo.find_all.return_value = mock_tasks
        
        result = self.service.list_tasks()
        
        assert len(result) == 2
        self.mock_task_repo.find_all.assert_called_once()

    def test_list_active_tasks(self):
        """测试列出活跃任务"""
        mock_tasks = [
            Task(task_id="task1", task_type=TaskType.DOWNLOAD, status=TaskStatus.RUNNING),
            Task(task_id="task2", task_type=TaskType.TRANSCRIBE, status=TaskStatus.PENDING),
        ]
        self.mock_task_repo.find_active.return_value = mock_tasks
        
        result = self.service.list_active_tasks()
        
        assert len(result) == 2
        self.mock_task_repo.find_active.assert_called_once()

    def test_start_task(self):
        """测试开始任务"""
        mock_task = Task(task_id="task1", task_type=TaskType.DOWNLOAD, status=TaskStatus.PENDING)
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        self.service.start_task("task1")
        
        assert mock_task.status == TaskStatus.RUNNING
        self.mock_task_repo.save.assert_called_once()

    def test_start_task_not_found(self):
        """测试开始不存在的任务"""
        self.mock_task_repo.find_by_id.return_value = None
        
        self.service.start_task("task1")
        
        self.mock_task_repo.save.assert_not_called()

    def test_complete_task(self):
        """测试完成任务"""
        mock_task = Task(task_id="task1", task_type=TaskType.DOWNLOAD, status=TaskStatus.RUNNING)
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        self.service.complete_task("task1")
        
        assert mock_task.status == TaskStatus.COMPLETED
        self.mock_task_repo.save.assert_called_once()

    def test_fail_task(self):
        """测试任务失败"""
        mock_task = Task(task_id="task1", task_type=TaskType.DOWNLOAD, status=TaskStatus.RUNNING)
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        self.service.fail_task("task1", "下载失败")
        
        assert mock_task.status == TaskStatus.FAILED
        assert mock_task.error_msg == "下载失败"
        self.mock_task_repo.save.assert_called_once()

    def test_cancel_task(self):
        """测试取消任务"""
        mock_task = Task(task_id="task1", task_type=TaskType.DOWNLOAD, status=TaskStatus.RUNNING)
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        self.service.cancel_task("task1")
        
        assert mock_task.status == TaskStatus.CANCELLED
        self.mock_task_repo.save.assert_called_once()

    def test_update_task_progress(self):
        """测试更新任务进度"""
        mock_task = Task(task_id="task1", task_type=TaskType.DOWNLOAD)
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        self.service.update_task_progress("task1", 0.5, "正在下载")
        
        assert mock_task.progress == 0.5
        assert mock_task.payload.get("msg") == "正在下载"
        self.mock_task_repo.save.assert_called_once()

    def test_clear_task_history(self):
        """测试清空任务历史"""
        self.service.clear_task_history()
        
        self.mock_task_repo.clear_history.assert_called_once()