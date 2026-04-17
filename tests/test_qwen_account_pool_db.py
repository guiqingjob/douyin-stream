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


def test_add_qwen_account_sets_auth_state_path(monkeypatch) -> None:
    import sqlite3
    from media_tools.api.routers import settings as settings_router

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE Accounts_Pool(account_id TEXT PRIMARY KEY, platform TEXT, cookie_data TEXT, remark TEXT, status TEXT DEFAULT 'active', auth_state_path TEXT DEFAULT '')"
    )
    conn.commit()
    monkeypatch.setattr("media_tools.api.routers.settings.get_db_connection", lambda: conn)

    called = {}

    def _fake_save(cookie_string: str, auth_state_path, **kwargs):  # noqa: ANN001
        called["auth_state_path"] = str(auth_state_path)
        return {}

    monkeypatch.setattr("media_tools.api.routers.settings.save_qwen_cookie_string", _fake_save)

    req = settings_router.QwenAccountRequest(cookie_string="x=y", remark="r")
    result = settings_router.add_qwen_account(req)
    account_id = result["account_id"]
    row = conn.execute("SELECT auth_state_path FROM Accounts_Pool WHERE account_id=?", (account_id,)).fetchone()
    assert row is not None
    assert row[0]
    assert "qwen-storage-state-" in row[0]
    assert called["auth_state_path"] == row[0]
