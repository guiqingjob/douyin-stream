from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from media_tools.services import task_ops


@pytest.mark.asyncio
async def test_complete_task_failed_sets_progress_zero() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE task_queue (
            task_id TEXT PRIMARY KEY,
            task_type TEXT,
            status TEXT,
            progress REAL,
            payload TEXT,
            create_time TEXT,
            update_time TEXT,
            error_msg TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, status, progress, payload, create_time, update_time, error_msg)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("t1", "pipeline", "RUNNING", 0.0, "{}", "2026-04-27T00:00:00", "2026-04-27T00:00:00", None),
    )
    conn.commit()

    notify = AsyncMock()
    with patch.object(task_ops, "get_db_connection", return_value=conn), patch.object(
        task_ops, "notify_task_update", new=notify
    ):
        await task_ops._complete_task("t1", "pipeline", "fail", status="FAILED", error_msg="boom")

    assert notify.await_args.args[1] == 0.0

