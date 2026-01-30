import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_endpoints(client):
    resp = client.get("/api/v1/discovery/endpoints")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Basic shape validation
    for item in data:
        assert "id" in item and "name" in item and "type" in item
