"""Tests for perceptual-hash orientation coverage."""

from __future__ import annotations

import pytest
from PIL import ImageOps

from leafcheck.hashing import hamming_min, orientation_hashes
from leafcheck.synth_data import gradient, noisy_blob, solid


def test_orientation_hashes_returns_eight() -> None:
    img = solid((120, 90, 60))
    hashes = orientation_hashes(img)
    assert len(hashes) == 8


def test_rotated_image_is_in_own_group() -> None:
    """A 90-deg rotation of an image must produce a hash that's equal to one
    of the 8 orientation-hashes of the original (since the 8 orientations
    form a group under rotation).
    """
    base = gradient(seed=42)
    rotated = base.rotate(90, expand=True)
    base_hashes = orientation_hashes(base)
    rotated_hashes = orientation_hashes(rotated)
    # The canonical (identity) hash of the rotated image should match one
    # of the 8 hashes of the original.
    assert rotated_hashes[0] in base_hashes


def test_mirrored_image_is_in_own_group() -> None:
    base = gradient(seed=42)
    mirrored = ImageOps.mirror(base)
    base_hashes = orientation_hashes(base)
    mirrored_hashes = orientation_hashes(mirrored)
    assert mirrored_hashes[0] in base_hashes


def test_different_images_are_far_apart() -> None:
    a = orientation_hashes(gradient(seed=1))
    b = orientation_hashes(noisy_blob(seed=999, label="very_different"))
    # noisy_blob has a flat background and a disk, gradient is smooth — these
    # are structurally very different, so the hashes should be far apart.
    assert hamming_min(a, b) > 8


def test_hamming_min_self_is_zero() -> None:
    a = orientation_hashes(noisy_blob(seed=7, label="alpha"))
    assert hamming_min(a, a) == 0


@pytest.mark.parametrize("k", [0, 90, 180, 270])
def test_rotation_by_k_is_covered(k: int) -> None:
    base = gradient(seed=123, size=(48, 48))
    rotated = base if k == 0 else base.rotate(k, expand=True)
    base_hashes = orientation_hashes(base)
    rotated_hashes = orientation_hashes(rotated)
    assert rotated_hashes[0] in base_hashes
