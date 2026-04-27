from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from media_tools.api.app import app


client = TestClient(app)


def test_update_global_settings_supports_patch_semantics() -> None:
    calls: list[tuple[str, object]] = []

    def _set(key: str, value: object) -> None:
        calls.append((key, value))

    with patch("media_tools.api.routers.settings.set_runtime_setting", side_effect=_set):
        resp = client.post("/api/v1/settings/global", json={"auto_transcribe": True})

    assert resp.status_code == 200
    assert calls == [("auto_transcribe", True)]


def test_update_global_settings_rejects_empty_patch() -> None:
    resp = client.post("/api/v1/settings/global", json={})
    assert resp.status_code == 400

