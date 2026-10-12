"""Model factory — MobileNetV3-Small with ImageNet-pretrained weights.

Per F3: "torchvision MobileNetV3-Small with ImageNet-pretrained weights".
We use `MobileNet_V3_Small_Weights.IMAGENET1K_V1` (the canonical 2024 default).
For CPU-only deployment we set `quantize=False`; the model is small enough
that quantization isn't worth the accuracy trade.
"""

from __future__ import annotations

import torch.nn as nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small


def build_model(num_classes: int, *, pretrained: bool = True) -> nn.Module:
    """Build a MobileNetV3-Small with a fresh `num_classes`-way classifier.

    `pretrained=True` uses ImageNet weights for the feature extractor
    (the classifier head is always re-initialized because the class count
    differs from 1000). On a CPU-only box the download happens once and is
    cached under `~/.cache/torch/hub/checkpoints/`.
    """
    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    model = mobilenet_v3_small(weights=weights)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)
    return model


def class_imbalance_ratio(class_counts: list[int]) -> float:
    """Return max_count / min_count. Used to decide on weighted loss (F3.AC5)."""
    if not class_counts:
        return 1.0
    return max(class_counts) / max(1, min(class_counts))
