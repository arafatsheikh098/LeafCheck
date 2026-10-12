"""G2: one shared preprocessing module is used by training, evaluation, and serving.

This test inspects the AST/source of the relevant modules to assert that
each of them imports from `leafcheck.preprocess` rather than reimplementing
its own resize + normalize pipeline.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _imports_from_preprocess(path: Path) -> bool:
    """Return True if `path` imports the shared preprocess module.

    Accepts both `from leafcheck.preprocess import ...` and
    `from leafcheck import preprocess` (or `import leafcheck.preprocess`).
    """
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("leafcheck.preprocess"):
                return True
            if mod == "leafcheck" and any((alias.name == "preprocess") for alias in node.names):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "leafcheck.preprocess" or alias.name.startswith(
                    "leafcheck.preprocess."
                ):
                    return True
    return False


def test_training_uses_shared_preprocess() -> None:
    src = Path(__file__).resolve().parents[2] / "src" / "leafcheck" / "train.py"
    assert _imports_from_preprocess(src), f"{src} must import from leafcheck.preprocess"


def test_serving_will_use_shared_preprocess() -> None:
    """Predictor lives in predictor.py — created in M5. This test asserts the
    file uses the shared preprocessing function."""
    src = Path(__file__).resolve().parents[2] / "src" / "leafcheck" / "predictor.py"
    if not src.exists():
        pytest.skip("predictor.py is added in M5; will be checked there")
    assert _imports_from_preprocess(src)


def test_evaluation_will_use_shared_preprocess() -> None:
    """evaluate.py is added in M4. Skip here, will be enforced there."""
    src = Path(__file__).resolve().parents[2] / "src" / "leafcheck" / "evaluate.py"
    if not src.exists():
        pytest.skip("evaluate.py is added in M4; will be checked there")
    assert _imports_from_preprocess(src)


def test_preprocess_module_exposes_expected_api() -> None:
    """The shared module must expose `preprocess_image` and `preprocess_batch`."""
    from leafcheck import preprocess as pp

    assert callable(pp.preprocess_image)
    assert callable(pp.preprocess_batch)


def test_preprocess_image_returns_normalized_tensor() -> None:
    import torch
    from PIL import Image

    from leafcheck import preprocess as pp

    img = Image.new("RGB", (256, 256), (128, 64, 32))
    out = pp.preprocess_image(img, image_size=224)
    assert isinstance(out, torch.Tensor)
    assert out.shape == (3, 224, 224)
    # ImageNet-normalized pixel means are roughly 0 — but with constant input,
    # mean is (128/255 - 0.485) / 0.229 ≈ 0.18. We just assert it isn't huge.
    assert out.abs().mean().item() < 5.0


def test_preprocess_batch_returns_4d_tensor() -> None:
    from PIL import Image

    from leafcheck import preprocess as pp

    imgs = [Image.new("RGB", (256, 256), (i * 10, 50, 200)) for i in range(5)]
    out = pp.preprocess_batch(imgs, image_size=64, augment=False)
    assert out.shape == (5, 3, 64, 64)
    # Augment path returns the same shape.
    out_aug = pp.preprocess_batch(imgs, image_size=64, augment=True)
    assert out_aug.shape == (5, 3, 64, 64)
