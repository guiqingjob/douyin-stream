"""Tests for TaskService."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from media_tools.services.task_service import TaskService, get_task_service


class TaskServiceTests(unittest.TestCase):
    """Tests for TaskService."""

    def test_service_is_singleton(self) -> None:
        """Test get_task_service returns singleton."""
        s1 = get_task_service()
        s2 = get_task_service()
        self.assertIs(s1, s2)

    @patch("media_tools.services.task_service.TaskRepository")
    def test_get_active_tasks(self, mock_repo: MagicMock) -> None:
        """Test get_active_tasks."""
        mock_repo.find_active.return_value = []
        result = TaskService.get_active_tasks()
        mock_repo.find_active.assert_called_once()
        self.assertEqual(result, [])

    @patch("media_tools.services.task_service.TaskRepository")
    def test_get_task_history(self, mock_repo: MagicMock) -> None:
        """Test get_task_history."""
        mock_repo.list_recent.return_value = []
        result = TaskService.get_task_history()
        mock_repo.list_recent.assert_called_once()
        self.assertEqual(result, [])

    @patch("media_tools.services.task_service.TaskRepository")
    def test_clear_task_history(self, mock_repo: MagicMock) -> None:
        """Test clear_task_history."""
        result = TaskService.clear_task_history()
        mock_repo.clear_history.assert_called_once()
        self.assertEqual(result, {"status": "ok"})

    @patch("media_tools.services.task_service.TaskRepository")
    def test_get_task_status_not_found(self, mock_repo: MagicMock) -> None:
        """Test get_task_status when task not found."""
        mock_repo.find_by_id.return_value = None
        result = TaskService.get_task_status("nonexistent")
        self.assertEqual(result["status"], "not_found")

    @patch("media_tools.services.task_service.cleanup_stale_tasks")
    def test_cleanup_stale_tasks(self, mock_cleanup: MagicMock) -> None:
        """Test cleanup_stale_tasks."""
        mock_cleanup.return_value = 5
        result = TaskService.cleanup_stale_tasks()
        mock_cleanup.assert_called_once()
        self.assertEqual(result, {"removed": 5})


if __name__ == "__main__":
    unittest.main()