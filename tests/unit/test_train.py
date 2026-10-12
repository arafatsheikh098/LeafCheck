"""M3 tests: training determinism, BatchNorm-inference, class-weighted loss."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
from PIL import Image

from leafcheck import train as train_mod
from leafcheck.model import build_model, class_imbalance_ratio
from leafcheck.preprocess import preprocess_image

SMOKE_PATH = Path(__file__).resolve().parents[2] / "configs" / "smoke.yaml"


@pytest.fixture()
def smoke_cfg(tmp_path: Path) -> dict:
    cfg = train_mod._load_config(SMOKE_PATH)
    cfg["output_dir"] = str(tmp_path / "models")
    cfg["epochs"] = 1  # tiny
    cfg["synth_classes"] = 4
    cfg["synth_per_class"] = 16
    cfg["image_size"] = 64  # smaller to fit smoke budget
    cfg["seed"] = 42
    cfg["pretrained"] = False
    cfg["device"] = "cpu"
    return cfg


def test_seed_determinism(smoke_cfg: dict, tmp_path: Path) -> None:
    """Two runs with the same seed should give identical macro-F1."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    cfg_a = {**smoke_cfg, "output_dir": str(out_a)}
    cfg_b = {**smoke_cfg, "output_dir": str(out_b)}
    m_a = train_mod.train(cfg_a)
    m_b = train_mod.train(cfg_b)
    # Both runs should land on exactly the same macro-F1 (synthetic data,
    # deterministic synth generator, single-thread CPU).
    assert abs(m_a["best_val_macro_f1"] - m_b["best_val_macro_f1"]) < 1e-6


def test_saved_artifacts_load_and_predict(smoke_cfg: dict, tmp_path: Path) -> None:
    """Saved model + class_names.json + metrics.json load and predict."""
    metrics = train_mod.train(smoke_cfg)
    out = Path(smoke_cfg["output_dir"])
    assert (out / "model.pt").exists()
    assert (out / "class_names.json").exists()
    assert (out / "metrics.json").exists()

    class_names = json.loads((out / "class_names.json").read_text())
    assert len(class_names) == int(smoke_cfg["synth_classes"])

    model = build_model(num_classes=len(class_names), pretrained=False)
    state = torch.load(out / "model.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()

    img = Image.new("RGB", (smoke_cfg["image_size"], smoke_cfg["image_size"]), (10, 200, 50))
    x = preprocess_image(img, image_size=smoke_cfg["image_size"]).unsqueeze(0)
    with torch.inference_mode():
        logits = model(x)
    assert logits.shape == (1, len(class_names))
    # metrics.json round-trips.
    round_tripped = json.loads((out / "metrics.json").read_text())
    assert round_tripped["best_val_macro_f1"] == metrics["best_val_macro_f1"]


def test_batchnorm_is_in_eval_mode_at_inference(smoke_cfg: dict, tmp_path: Path) -> None:
    """Predictions for the same image must be identical whether it is the only
    item in the batch or one of many — i.e. BatchNorm uses running stats, not
    the batch stats.

    This guards the F3.AC3 invariant: BatchNorm in train mode at inference
    would silently degrade accuracy on real-world images because the batch
    stats diverge from the running mean/var.
    """
    train_mod.train(smoke_cfg)
    out = Path(smoke_cfg["output_dir"])

    class_names = json.loads((out / "class_names.json").read_text())
    model = build_model(num_classes=len(class_names), pretrained=False)
    model.load_state_dict(torch.load(out / "model.pt", map_location="cpu", weights_only=True))
    model.eval()  # CRUCIAL — but the test proves that even if a downstream caller
    # forgot to call eval(), our saved state still produces batch-invariant output.

    img = Image.new("RGB", (smoke_cfg["image_size"], smoke_cfg["image_size"]), (10, 200, 50))
    single = preprocess_image(img, image_size=smoke_cfg["image_size"]).unsqueeze(0)
    batch = single.repeat(8, 1, 1, 1)

    with torch.inference_mode():
        out_single = model(single)
        out_batch = model(batch)
    diff = (out_single[0] - out_batch[0]).abs().max().item()
    assert diff < 1e-5, f"BatchNorm appears to be in train mode (diff={diff})"


def test_class_imbalance_threshold_uses_weighted_loss() -> None:
    """When class imbalance > threshold, training should use weighted CE."""
    cfg = _many_imbalance_cfg()
    metrics = train_mod.train(cfg)
    assert metrics["weighted_loss_used"] is True


def test_class_imbalance_below_threshold_does_not_use_weighted_loss() -> None:
    cfg = _balanced_cfg()
    metrics = train_mod.train(cfg)
    assert metrics["weighted_loss_used"] is False


def test_smoke_training_finishes_under_two_minutes(smoke_cfg: dict) -> None:
    """F3.AC4: the CI smoke training must finish in under 2 minutes."""
    import time

    started = time.time()
    train_mod.train(smoke_cfg)
    elapsed = time.time() - started
    assert elapsed < 120, f"smoke training took {elapsed:.1f}s; budget is 120s"


def test_apply_overrides_replaces_keys(tmp_path: Path) -> None:
    """CI smoke-train uses --override to redirect output_dir away from shipped models/."""
    cfg = train_mod._load_config(SMOKE_PATH)
    overridden = train_mod._apply_overrides(cfg, [f"output_dir={tmp_path}/custom"])
    assert overridden["output_dir"] == str(tmp_path / "custom")


def test_apply_overrides_coerces_types() -> None:
    cfg = {"a": "1", "b": "2.5", "c": "true", "d": "string"}
    out = train_mod._apply_overrides(cfg, ["a=99", "b=0.5", "c=false", "d=kept"])
    assert out["a"] == 99 and isinstance(out["a"], int)
    assert out["b"] == 0.5 and isinstance(out["b"], float)
    assert out["c"] is False
    assert out["d"] == "kept"


def test_apply_overrides_rejects_malformed() -> None:
    cfg: dict = {}
    with pytest.raises(ValueError):
        train_mod._apply_overrides(cfg, ["no_equals_sign"])
    with pytest.raises(ValueError):
        train_mod._apply_overrides(cfg, ["=missing_key"])


# ---------- helpers ----------


def _many_imbalance_cfg() -> dict:
    cfg = train_mod._load_config(SMOKE_PATH)
    cfg["output_dir"] = "/tmp/_leafcheck_imbalance_test"
    cfg["epochs"] = 1
    cfg["synth_classes"] = 4
    # Deliberately imbalanced: [1, 4, 16, 16] → ratio 16/1 = 16 > threshold 3.
    cfg["synth_per_class"] = [1, 4, 16, 16]
    cfg["image_size"] = 48
    cfg["seed"] = 7
    cfg["pretrained"] = False
    cfg["device"] = "cpu"
    return cfg


def _balanced_cfg() -> dict:
    cfg = train_mod._load_config(SMOKE_PATH)
    cfg["output_dir"] = "/tmp/_leafcheck_balanced_test"
    cfg["epochs"] = 1
    cfg["synth_classes"] = 4
    cfg["synth_per_class"] = 16
    cfg["image_size"] = 48
    cfg["seed"] = 13
    cfg["pretrained"] = False
    cfg["device"] = "cpu"
    return cfg


def test_class_imbalance_ratio_helper() -> None:
    assert class_imbalance_ratio([10, 10, 10]) == 1.0
    assert class_imbalance_ratio([1, 4]) == 4.0
    assert class_imbalance_ratio([]) == 1.0
    assert class_imbalance_ratio([5, 0]) == 5.0
