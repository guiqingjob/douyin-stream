from __future__ import annotations

import sqlite3


def test_db_init_adds_media_assets_folder_path(tmp_path) -> None:
    from media_tools.db.core import init_db

    db_path = tmp_path / "t.db"
    init_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cols = [row[1] for row in conn.execute("PRAGMA table_info(media_assets)").fetchall()]
    assert "folder_path" in cols


def test_local_transcribe_request_accepts_directory_root() -> None:
    from media_tools.api.routers.tasks import LocalTranscribeRequest

    req = LocalTranscribeRequest(
        file_paths=["/tmp/a.mp3"],
        delete_after=False,
        directory_root="/tmp",
    )
    assert req.directory_root == "/tmp"
