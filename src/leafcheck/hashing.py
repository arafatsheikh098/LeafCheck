"""Perceptual hashing with full D4 (8-orientation) coverage.

The D4 group contains the 8 symmetries of the square: identity, 90/180/270
rotations, and 4 mirrors. We hash all 8 representations of every image so two
augmented copies of the same leaf land in the same group even if one has been
flipped or rotated.
"""

from __future__ import annotations

from collections.abc import Iterable

import imagehash
from PIL import Image


def _d4_views(img: Image.Image) -> list[Image.Image]:
    """Return the 8 D4 orientations: 4 rotations x {identity, mirror}."""
    views: list[Image.Image] = []
    for k in (0, 1, 2, 3):
        rotated = img if k == 0 else img.rotate(90 * k, expand=True)
        views.append(rotated)
        views.append(rotated.transpose(Image.FLIP_LEFT_RIGHT))
    return views


def orientation_hashes(img: Image.Image, hash_size: int = 8) -> list[imagehash.ImageHash]:
    """Compute perceptual hashes for all 8 D4 orientations of `img`."""
    return [imagehash.phash(v, hash_size=hash_size) for v in _d4_views(img)]


def group_id_for(hashes: Iterable[imagehash.ImageHash]) -> list[str]:
    """Stable canonical string for each hash (used in the group graph)."""
    return [str(h) for h in hashes]


def hamming_min(a: Iterable[imagehash.ImageHash], b: Iterable[imagehash.ImageHash]) -> int:
    """Smallest Hamming distance between any hash in `a` and any in `b`."""
    return min((x - y) for x in a for y in b)
