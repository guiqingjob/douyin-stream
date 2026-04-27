import json
import sqlite3
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from media_tools.api.app import app


def test_task_history_injects_pipeline_progress_into_payload() -> None:
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
    now = datetime.now().isoformat()
    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("t-p1", "pipeline", json.dumps({"msg": "x"}, ensure_ascii=False), "RUNNING", 0.2, "", now, now),
    )
    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("t-p2", "pipeline", json.dumps({"msg": "y"}, ensure_ascii=False), "RUNNING", 0.7, "", now, now),
    )
    conn.execute(
        """
        INSERT INTO task_queue(task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("t-other", "download", json.dumps({"msg": "z"}, ensure_ascii=False), "RUNNING", 0.3, "", now, now),
    )
    conn.commit()

    with patch("media_tools.api.routers.tasks.get_db_connection", return_value=conn), patch(
        "media_tools.repositories.task_repository.get_db_connection", return_value=conn
    ):
        client = TestClient(app)
        resp = client.get("/api/v1/tasks/history")

    assert resp.status_code == 200
    tasks = resp.json()
    by_id = {t["task_id"]: t for t in tasks}

    payload_1 = json.loads(by_id["t-p1"]["payload"])
    assert payload_1["pipeline_progress"]["stage"] == "downloading"
    assert payload_1["pipeline_progress"]["overall_progress"] == pytest.approx(0.2)
    assert payload_1["pipeline_progress"]["stage_progress"] == pytest.approx(0.2 / 0.4)

    payload_2 = json.loads(by_id["t-p2"]["payload"])
    assert payload_2["pipeline_progress"]["stage"] == "transcribing"
    assert payload_2["pipeline_progress"]["overall_progress"] == pytest.approx(0.7)
    assert payload_2["pipeline_progress"]["stage_progress"] == pytest.approx((0.7 - 0.4) / 0.6)

    payload_other = json.loads(by_id["t-other"]["payload"])
    assert "pipeline_progress" not in payload_other
