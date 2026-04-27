import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from media_tools.api.app import app

client = TestClient(app)

def test_get_assets_by_creator():
    response = client.get("/api/v1/assets/?creator_uid=123")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_bulk_delete_does_not_begin_immediate_before_file_delete():
    from media_tools.db.core import init_db
    from media_tools.api.routers import assets as assets_router

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        db_path = root / "test.db"
        init_db(db_path)

        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        downloads = root / "downloads"
        transcripts = root / "transcripts"
        downloads.mkdir(parents=True, exist_ok=True)
        transcripts.mkdir(parents=True, exist_ok=True)

        (downloads / "v.mp4").write_bytes(b"x")
        (transcripts / "t.txt").write_text("x", encoding="utf-8")

        conn.execute(
            """
            INSERT INTO media_assets
            (asset_id, creator_uid, source_url, title, video_path, video_status, transcript_path, transcript_status, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "a1",
                "c1",
                None,
                "t",
                "v.mp4",
                "ready",
                "t.txt",
                "ready",
                "2026-04-27T00:00:00",
                "2026-04-27T00:00:00",
            ),
        )
        conn.commit()

        began = {"value": False}

        class _ConnProxy:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def execute(self, sql, params=()):
                if sql == "BEGIN IMMEDIATE":
                    began["value"] = True
                return self._inner.execute(sql, params)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _delete_asset_files(*_args, **_kwargs):
            assert began["value"] is False
            return []

        with patch.object(assets_router, "get_db_connection", return_value=_ConnProxy(conn)), patch.object(
            assets_router, "get_download_path", return_value=downloads
        ), patch.object(assets_router, "get_project_root", return_value=root), patch.object(
            assets_router, "delete_asset_files", side_effect=_delete_asset_files
        ):
            resp = client.post("/api/v1/assets/bulk_delete", json={"ids": ["a1"]})

        assert resp.status_code == 200
        assert began["value"] is True


def test_get_asset_transcript_missing_file_does_not_write_db() -> None:
    from media_tools.db.core import init_db
    from media_tools.api.routers import assets as assets_router

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        db_path = root / "test.db"
        init_db(db_path)

        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        conn.execute(
            """
            INSERT INTO media_assets
            (asset_id, creator_uid, source_url, title, video_path, video_status, transcript_path, transcript_status, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "a1",
                "c1",
                None,
                "t",
                None,
                "ready",
                "missing.md",
                "ready",
                "2026-04-27T00:00:00",
                "2026-04-27T00:00:00",
            ),
        )
        conn.commit()

        with patch.object(assets_router, "get_db_connection", return_value=conn), patch.object(
            assets_router, "get_project_root", return_value=root
        ):
            resp = client.get("/api/v1/assets/a1/transcript")

        assert resp.status_code == 404
        status = conn.execute(
            "SELECT transcript_status FROM media_assets WHERE asset_id = ?",
            ("a1",),
        ).fetchone()["transcript_status"]
        assert status == "ready"
