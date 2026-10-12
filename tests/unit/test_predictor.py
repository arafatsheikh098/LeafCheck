"""F5 tests: Predictor logic with a real (smoke) model.

We use the smoke-trained model from `tests/_smoke_data` and a freshly
trained micro-model for the mocked-logits test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from leafcheck import train as train_mod
from leafcheck.predictor import Predictor, ThresholdConfig


def _train_tiny_model(tmp_path: Path) -> Path:
    cfg = {
        "seed": 7,
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
        "synth_per_class": 16,
    }
    train_mod.train(cfg)
    return tmp_path / "models"


def test_predictor_loads_smoke_model(tmp_path: Path) -> None:
    model_dir = _train_tiny_model(tmp_path)
    p = Predictor(model_dir)
    assert p.class_names
    assert p.image_size == 32
    img = Image.new("RGB", (48, 48), (123, 200, 50))
    pred = p.predict(img)
    assert isinstance(pred.class_name, str)
    assert 0.0 <= pred.confidence <= 1.0
    # No threshold file by default, so not_sure is False.
    assert pred.not_sure is False


def test_predictor_threshold_below_marks_not_sure(tmp_path: Path) -> None:
    model_dir = _train_tiny_model(tmp_path)
    p = Predictor(model_dir)
    # Force the threshold to 0.99 — almost every prediction will be below.
    p.threshold = ThresholdConfig(
        threshold=0.99,
        target_precision=0.95,
        val_precision_at_threshold=1.0,
        val_coverage_at_threshold=0.0,
    )
    img = Image.new("RGB", (48, 48), (0, 0, 0))
    pred = p.predict(img)
    assert pred.not_sure is True


def test_predictor_threshold_above_does_not_mark_not_sure(tmp_path: Path) -> None:
    model_dir = _train_tiny_model(tmp_path)
    p = Predictor(model_dir)
    # Force the threshold to 0.0 — every prediction will be above.
    p.threshold = ThresholdConfig(
        threshold=0.0,
        target_precision=0.95,
        val_precision_at_threshold=1.0,
        val_coverage_at_threshold=1.0,
    )
    img = Image.new("RGB", (48, 48), (0, 0, 0))
    pred = p.predict(img)
    assert pred.not_sure is False


def test_predictor_missing_model_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Predictor(tmp_path)


def test_predictor_class_count_mismatch_raises(tmp_path: Path) -> None:
    """F5.AC3: class-count mismatch between model and class_names.json."""
    from leafcheck.predictor import Predictor

    # Train a 4-class model, then write a 5-class class_names.json that
    # the model can't load.
    model_dir = _train_tiny_model(tmp_path)
    import json

    (model_dir / "class_names.json").write_text(json.dumps(["a", "b", "c", "d", "e"]))
    with pytest.raises(RuntimeError, match="classes"):
        Predictor(model_dir)
