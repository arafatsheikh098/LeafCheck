"""M1 acceptance: GET /health returns 200 with the expected JSON."""

from fastapi.testclient import TestClient

from leafcheck.api import reset_singletons
from leafcheck.app.main import create_app


def test_health_returns_ok(monkeypatch, tmp_path) -> None:
    # Force a clean app for this test: point LEAFCHECK_MODEL_DIR at a
    # tmp dir that doesn't have a model, so the predictor is "degraded".
    # The M1 contract only requires the key 'model_loaded' to be present
    # and the service to be reachable.
    monkeypatch.setenv("LEAFCHECK_MODEL_DIR", str(tmp_path / "no_models_here"))
    reset_singletons()
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert body["service"] == "leafcheck"
    # model_loaded is wired up properly in M5; M1 just needs the key present.
    assert "model_loaded" in body
    # In M5, when no model is available, model_loaded is False.
    assert body["model_loaded"] is False
