"""G5: each `examples/` file returns its expected class via the real API.

These examples and the smoke model that classifies them are both
synthetic — see `examples/README.md` and DECISIONS.md D8. The test
verifies the *plumbing*: a fresh FastAPI app started against the
shipped `models/` predicts the class listed in `examples/labels.json`
for every shipped example.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leafcheck.api import reset_singletons

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"
LABELS_FILE = EXAMPLES_DIR / "labels.json"
MODELS_DIR = REPO_ROOT / "models"
ADVICE_PATH = REPO_ROOT / "data" / "advice.json"


@pytest.fixture(scope="module")
def examples_client() -> TestClient:
    if not LABELS_FILE.exists():
        pytest.skip(f"{LABELS_FILE} not present; M7 not run yet")
    if not (MODELS_DIR / "model.pt").exists():
        pytest.skip("models/model.pt not present; smoke model not trained yet")
    os.environ["LEAFCHECK_MODEL_DIR"] = str(MODELS_DIR)
    os.environ["LEAFCHECK_ADVICE_PATH"] = str(ADVICE_PATH)
    reset_singletons()
    from leafcheck.app.main import create_app

    return TestClient(create_app())


def test_examples_round_trip(examples_client: TestClient) -> None:
    """G5: each file in examples/labels.json returns its expected class."""
    labels = json.loads(LABELS_FILE.read_text())
    mismatches: list[str] = []
    for fname, info in labels.items():
        path = EXAMPLES_DIR / fname
        assert path.exists(), f"missing example image {path}"
        data = path.read_bytes()
        r = examples_client.post(
            "/api/predict",
            files={"file": (fname, data, "image/jpeg")},
        )
        assert r.status_code == 200, f"{fname}: {r.status_code} {r.text}"
        body = r.json()
        predicted = body["class_name"]
        expected = info["expected_class"]
        if predicted != expected:
            mismatches.append(
                f"{fname}: predicted={predicted} (conf={body['confidence']:.3f}) "
                f"expected={expected}"
            )
    assert not mismatches, "examples did not round-trip:\n  " + "\n  ".join(mismatches)
