from __future__ import annotations

import sqlite3


def test_db_init_adds_accounts_pool_auth_state_path(tmp_path) -> None:
    from media_tools.db.core import init_db

    db_path = tmp_path / "t.db"
    init_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cols = [row[1] for row in conn.execute("PRAGMA table_info(Accounts_Pool)").fetchall()]
    assert "auth_state_path" in cols


def test_build_qwen_auth_state_path_for_account() -> None:
    from media_tools.transcribe.db_account_pool import build_qwen_auth_state_path_for_account

    p = build_qwen_auth_state_path_for_account("abc123")
    assert p.name == "qwen-storage-state-abc123.json"
