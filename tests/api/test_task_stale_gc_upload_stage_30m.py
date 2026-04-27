import json
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from media_tools.api.app import app

client = TestClient(app)


def test_task_stale_gc_upload_stage_uses_30m(monkeypatch) -> None:
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
    payload_upload = json.dumps({"pipeline_progress": {"stage": "upload"}}, ensure_ascii=False)
    payload_other = json.dumps({"pipeline_progress": {"stage": "transcribe"}}, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "t-upload-25m",
            "pipeline",
            payload_upload,
            "RUNNING",
            0.1,
            "",
            now.isoformat(),
            (now - timedelta(minutes=25)).isoformat(),
        ),
    )
    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "t-upload-35m",
            "pipeline",
            payload_upload,
            "RUNNING",
            0.1,
            "",
            now.isoformat(),
            (now - timedelta(minutes=35)).isoformat(),
        ),
    )
    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "t-other-25m",
            "pipeline",
            payload_other,
            "RUNNING",
            0.1,
            "",
            now.isoformat(),
            (now - timedelta(minutes=25)).isoformat(),
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
    by_id = {t["task_id"]: t for t in tasks}

    assert by_id["t-upload-25m"]["status"] == "RUNNING"
    assert by_id["t-upload-35m"]["status"] == "FAILED"
    assert by_id["t-other-25m"]["status"] == "FAILED"

