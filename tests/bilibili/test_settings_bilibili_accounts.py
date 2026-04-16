from __future__ import annotations

from fastapi.testclient import TestClient

from media_tools.api.app import app


client = TestClient(app)


def test_add_and_delete_bilibili_account() -> None:
    add_resp = client.post(
        "/api/v1/settings/bilibili/accounts",
        json={"cookie_string": "SESSDATA=xxx", "remark": "test"},
    )
    assert add_resp.status_code == 200
    account_id = add_resp.json()["account_id"]

    settings = client.get("/api/v1/settings/").json()
    ids = {a["id"] for a in settings.get("bilibili_accounts", [])}
    assert account_id in ids

    del_resp = client.delete(f"/api/v1/settings/bilibili/accounts/{account_id}")
    assert del_resp.status_code == 200

