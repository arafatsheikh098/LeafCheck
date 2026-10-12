"""M1 acceptance: GET /health returns 200 with the expected JSON."""

from fastapi.testclient import TestClient

from leafcheck.app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "leafcheck"
    # model_loaded is wired up properly in M5; M1 just needs the key present.
    assert "model_loaded" in body
