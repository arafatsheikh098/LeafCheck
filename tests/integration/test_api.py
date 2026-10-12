"""F5 integration tests: full FastAPI app."""

from __future__ import annotations

import io
import json
import os
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from leafcheck import train as train_mod
from leafcheck.api import reset_singletons


@pytest.fixture
def trained_model_dir(tmp_path: Path) -> Path:
    cfg = {
        "seed": 11,
        "image_size": 32,
        "epochs": 1,
        "batch_size": 8,
        "lr": 0.01,
        "optimizer": "sgd",
        "momentum": 0.9,
        "weight_decay": 1e-4,
        "early_stop_patience": 2,
        "imbalance_threshold": 3.0,
        "pretrained": False,
        "device": "cpu",
        "data_root": str(tmp_path / "manifest.csv"),
        "output_dir": str(tmp_path / "models"),
        "synth_classes": 4,
        "synth_per_class": 12,
    }
    train_mod.train(cfg)
    # Drop a threshold.json so the predictor runs the not_sure gate.
    (tmp_path / "models" / "threshold.json").write_text(
        json.dumps(
            {
                "threshold": 0.5,
                "target_precision": 0.95,
                "val_precision_at_threshold": 0.95,
                "val_coverage_at_threshold": 0.5,
                "test_coverage_at_threshold": 0.5,
            }
        )
    )
    return tmp_path / "models"


@pytest.fixture
def advice_file(tmp_path: Path) -> Path:
    p = tmp_path / "advice.json"
    p.write_text(
        json.dumps(
            {
                "class_0": {
                    "en": "This is a test English advice.",
                    "bn": "এটি একটি পরীক্ষামূলক বাংলা পরামর্শ।",
                    "reviewed_by_human": False,
                }
            }
        )
    )
    return p


def _jpeg_bytes(color=(100, 200, 50)) -> bytes:
    img = Image.new("RGB", (48, 48), color)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()


@pytest.fixture
def client(trained_model_dir: Path, advice_file: Path) -> TestClient:
    os.environ["LEAFCHECK_MODEL_DIR"] = str(trained_model_dir)
    os.environ["LEAFCHECK_ADVICE_PATH"] = str(advice_file)
    reset_singletons()
    # We need to import after env vars are set.
    from leafcheck.app.main import create_app

    app = create_app()
    return TestClient(app)


def test_health_reports_model_loaded(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["model_loaded"] is True
    assert body["service"] == "leafcheck"


def test_classes_endpoint(client: TestClient) -> None:
    r = client.get("/api/classes")
    assert r.status_code == 200
    assert len(r.json()["classes"]) == 4


def test_model_info_endpoint(client: TestClient) -> None:
    r = client.get("/api/model-info")
    assert r.status_code == 200
    body = r.json()
    assert body["model_loaded"] is True
    assert body["num_classes"] == 4
    assert body["image_size"] == 32
    assert body["threshold"] is not None
    assert body["threshold"]["threshold"] == 0.5
    # The test's model is trained at image_size=32 (see trained_model_dir fixture).


def test_predict_ok(client: TestClient) -> None:
    r = client.post(
        "/api/predict",
        files={"file": ("leaf.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert "class_name" in body
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["not_sure"], bool)
    assert len(body["top_k"]) >= 1


def test_predict_rejects_text_file(client: TestClient) -> None:
    r = client.post(
        "/api/predict",
        files={"file": ("leaf.jpg", b"this is not an image", "image/jpeg")},
    )
    assert r.status_code == 400
    assert "JPEG" in r.json()["detail"]


def test_predict_rejects_empty(client: TestClient) -> None:
    r = client.post(
        "/api/predict",
        files={"file": ("leaf.jpg", b"", "image/jpeg")},
    )
    assert r.status_code == 400
    assert "empty" in r.json()["detail"]


def test_predict_rejects_oversize(client: TestClient) -> None:
    big = b"\xff\xd8\xff" + b"\x00" * (5 * 1024 * 1024 + 10)
    r = client.post(
        "/api/predict",
        files={"file": ("leaf.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 400
    assert "MB" in r.json()["detail"]


def test_parallel_predicts_succeed(client: TestClient) -> None:
    """F5.AC5: fire two parallel /api/predict calls and both succeed."""
    results: list[int] = []
    errors: list[str] = []

    def _do() -> None:
        try:
            r = client.post(
                "/api/predict",
                files={"file": ("leaf.jpg", _jpeg_bytes(), "image/jpeg")},
            )
            results.append(r.status_code)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    t1 = threading.Thread(target=_do)
    t2 = threading.Thread(target=_do)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, errors
    assert results == [200, 200]


def test_startup_fails_on_missing_model(tmp_path: Path) -> None:
    """F5.AC3: if model files are missing, /health reports degraded."""
    os.environ["LEAFCHECK_MODEL_DIR"] = str(tmp_path / "no_models_here")
    reset_singletons()
    from leafcheck.app.main import create_app

    app = create_app()
    c = TestClient(app)
    r = c.get("/health")
    assert r.json()["model_loaded"] is False
