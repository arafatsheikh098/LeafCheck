"""Shared image preprocessing (G2).

Training, evaluation, and serving MUST all import and call this module.
A test asserts that they all import from `leafcheck.preprocess` rather than
implementing their own resize/normalize logic.
"""

from __future__ import annotations

import torch
from PIL import Image
from torchvision import transforms

# ImageNet normalization used by torchvision's pretrained MobileNetV3.
IMAGENET_MEAN: tuple[float, float, float] = (0.485, 0.456, 0.406)
IMAGENET_STD: tuple[float, float, float] = (0.229, 0.224, 0.225)

# Square input size. MobileNetV3-Small expects 224 but a smaller size is
# acceptable for our CPU-only deployment (F3.AC4: smoke training < 2 min).
DEFAULT_IMAGE_SIZE: int = 224


def make_eval_transform(image_size: int = DEFAULT_IMAGE_SIZE) -> transforms.Compose:
    """Deterministic preprocessing used by evaluation and serving.

    No random augmentation here — only resize + center-crop + normalize.
    """
    return transforms.Compose(
        [
            transforms.Resize(int(image_size * 1.14)),  # 256 for 224
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


def make_train_transform(image_size: int = DEFAULT_IMAGE_SIZE) -> transforms.Compose:
    """Preprocessing + augmentation used by training only.

    Per F3: "augmentation on the training split only".
    """
    return transforms.Compose(
        [
            transforms.Resize(int(image_size * 1.14)),
            transforms.RandomCrop(image_size),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


def preprocess_image(img: Image.Image, image_size: int = DEFAULT_IMAGE_SIZE) -> torch.Tensor:
    """Single-image entry point used by serving (`Predictor.predict`).

    Returns a CHW float tensor (C, H, W) with ImageNet normalization applied.
    """
    tfm = make_eval_transform(image_size)
    return tfm(img.convert("RGB"))


def preprocess_batch(
    imgs: list[Image.Image],
    image_size: int = DEFAULT_IMAGE_SIZE,
    augment: bool = False,
) -> torch.Tensor:
    """Batch entry point used by training and evaluation.

    Returns a BCHW float tensor. If `augment=True`, uses the training
    transform (random crop + flip + colour jitter).
    """
    tfm = make_train_transform(image_size) if augment else make_eval_transform(image_size)
    return torch.stack([tfm(img.convert("RGB")) for img in imgs])
