"""F5: model-serving `Predictor`.

The predictor wraps the model and threshold. It is loaded once at app
startup (F5.AC3) and reused for every request. `torch.inference_mode` is
used so BatchNorm running stats are stable (F3 correctness rule).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image

from leafcheck import preprocess as pp
from leafcheck.model import build_model


@dataclass
class ThresholdConfig:
    """The "not sure" threshold and the target precision it was tuned for."""

    threshold: float
    target_precision: float
    val_precision_at_threshold: float
    val_coverage_at_threshold: float


@dataclass
class Prediction:
    """Result of a single inference."""

    class_name: str
    confidence: float
    not_sure: bool
    top_k: list[dict]  # [{"class": str, "confidence": float}, ...]


class Predictor:
    """Loads model.pt + class_names.json + threshold.json once."""

    def __init__(
        self,
        model_dir: Path,
        *,
        top_k: int = 3,
        device: str = "cpu",
    ) -> None:
        self.model_dir = Path(model_dir)
        self.top_k = top_k
        self.device = device

        class_names_path = self.model_dir / "class_names.json"
        if not class_names_path.exists():
            raise FileNotFoundError(
                f"Missing {class_names_path}. Train first with `python -m leafcheck.train`."
            )
        self.class_names: list[str] = json.loads(class_names_path.read_text())
        if not self.class_names:
            raise ValueError("class_names.json is empty")

        model_path = self.model_dir / "model.pt"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Missing {model_path}. Train first with `python -m leafcheck.train`."
            )
        self.model = build_model(len(self.class_names), pretrained=False)
        state = torch.load(model_path, map_location="cpu", weights_only=True)
        try:
            self.model.load_state_dict(state)
        except RuntimeError as exc:
            raise RuntimeError(
                f"model.pt state dict doesn't match this architecture "
                f"(expected {len(self.class_names)} classes): {exc}"
            ) from exc
        self.model.eval()
        self.model.to(self.device)

        # Threshold: optional but expected. If absent, the predictor runs
        # without the "not sure" gate (not_sure will always be False).
        threshold_path = self.model_dir / "threshold.json"
        if threshold_path.exists():
            t = json.loads(threshold_path.read_text())
            self.threshold = ThresholdConfig(
                threshold=float(t["threshold"]),
                target_precision=float(t.get("target_precision", 0.95)),
                val_precision_at_threshold=float(t.get("val_precision_at_threshold", 0.0)),
                val_coverage_at_threshold=float(t.get("val_coverage_at_threshold", 0.0)),
            )
        else:
            self.threshold = None

        # Image size is read from the training metrics.json (saved by M3).
        metrics_path = self.model_dir / "metrics.json"
        if metrics_path.exists():
            self.image_size = int(json.loads(metrics_path.read_text()).get("image_size", 224))
        else:
            self.image_size = 224

    def predict(self, image: Image.Image) -> Prediction:
        """Run inference on a single PIL image and return a Prediction.

        The threshold check (F4.AC1) is applied here, AFTER the softmax
        is computed, so the confidence is the model probability.
        """
        with torch.inference_mode():
            x = pp.preprocess_image(image, image_size=self.image_size).unsqueeze(0)
            x = x.to(self.device)
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)[0]

        top_p, top_idx = torch.topk(probs, k=min(self.top_k, len(self.class_names)))
        top = [
            {"class": self.class_names[i], "confidence": float(p)}
            for p, i in zip(top_p.tolist(), top_idx.tolist(), strict=False)
        ]
        top_class = top[0]["class"]
        top_conf = top[0]["confidence"]
        not_sure = bool(self.threshold is not None and top_conf < self.threshold.threshold)
        return Prediction(
            class_name=top_class,
            confidence=top_conf,
            not_sure=not_sure,
            top_k=top,
        )
