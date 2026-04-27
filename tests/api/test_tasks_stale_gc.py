import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from media_tools.api.app import app

client = TestClient(app)


def test_task_history_triggers_stale_gc(monkeypatch) -> None:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE task_queue (
            task_id TEXT PRIMARY KEY,
            task_type TEXT,
            payload TEXT,
            status TEXT,
            progress REAL,
            error_msg TEXT,
            create_time TEXT,
            update_time TEXT
        )
        """
    )

    now = datetime.now()
    stale_update_time = (now - timedelta(minutes=25)).isoformat()
    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "t-stale",
            "pipeline",
            "{}",
            "RUNNING",
            0.2,
            "",
            now.isoformat(),
            stale_update_time,
        ),
    )
    conn.commit()

    monkeypatch.setenv("MEDIA_TOOLS_TASK_STALE_MINUTES", "20")
    with patch("media_tools.api.routers.tasks.get_db_connection", return_value=conn), patch(
        "media_tools.repositories.task_repository.get_db_connection", return_value=conn
    ):
        resp = client.get("/api/v1/tasks/history")

    assert resp.status_code == 200
    tasks = resp.json()
    task = next(t for t in tasks if t["task_id"] == "t-stale")
    assert task["status"] == "FAILED"
    assert task["error_msg"]
