import pytest
from fastapi.testclient import TestClient
from media_tools.api.app import app

client = TestClient(app)

def test_get_assets_by_creator():
    response = client.get("/api/v1/assets/?creator_uid=123")
    assert response.status_code == 200
    assert isinstance(response.json(), list)