from fastapi.testclient import TestClient

from dhi.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Verifies the health endpoint returns the correct 200 payload."""
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "dhi"
    assert data["version"] == "0.1.0-dev"
