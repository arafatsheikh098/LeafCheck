"""Synthetic image generator for tests and CI smoke runs.

Produces deterministic solid-color and gradient images. The point is NOT to
look like real leaves — it's to give the data pipeline something with known
SHA-256s and known orientation-hash relationships, so we can prove the
leakage-safe split actually groups near-duplicates correctly.

Available generators:

* `solid(rgb, size)` — a single solid color. Two of these differ only in
  their color, so they should be in different groups.
* `gradient(seed, size)` — a deterministic linear gradient. Rotations and
  flips of the same gradient share orientation hashes, so they must land
  in the same group.
* `noisy_blob(seed, size, label)` — a colored disk on a contrasting
  background. The label argument changes the colors, so different labels
  produce different groups.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from pathlib import Path

from PIL import Image, ImageDraw


def solid(rgb: tuple[int, int, int], size: tuple[int, int] = (64, 64)) -> Image.Image:
    return Image.new("RGB", size, rgb)


def gradient(seed: int, size: tuple[int, int] = (64, 64)) -> Image.Image:
    rng = random.Random(seed)
    c1 = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
    c2 = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
    img = Image.new("RGB", size)
    px = img.load()
    w, h = size
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def noisy_blob(seed: int, size: tuple[int, int] = (64, 64), *, label: str = "x") -> Image.Image:
    rng = random.Random(seed + hash(label) % (2**32))
    bg = (rng.randint(0, 80), rng.randint(0, 80), rng.randint(0, 80))
    fg = (rng.randint(180, 255), rng.randint(180, 255), rng.randint(180, 255))
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    # Disk radius depends on size; centered.
    r = min(size) // 3
    cx, cy = size[0] // 2, size[1] // 2
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fg)
    return img


def make_corrupt_jpeg(path: Path) -> None:
    """Write a file that looks like a JPEG header but is truncated."""
    # JPEG SOI + APP0 (JFIF) marker, then 4 random bytes, then truncated.
    path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff")


def write_tree(
    base: Path,
    files: Iterable[tuple[str, str]],
) -> None:
    """Write `(relative_path, generator_name)` pairs under `base/`.

    `generator_name` keys into `_GENERATORS`. We do not pass generator
    arguments through the string for safety; the synthetic fixtures are
    enumerated by the caller.
    """
    base.mkdir(parents=True, exist_ok=True)
    for relpath, generator_name in files:
        out = base / relpath
        out.parent.mkdir(parents=True, exist_ok=True)
        if generator_name == "corrupt":
            make_corrupt_jpeg(out)
            continue
        gen = _GENERATORS[generator_name]
        img = gen()
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(out, format="JPEG", quality=92)


# Fixed generator catalogue used by the synth fixtures.
def _g_solid_a() -> Image.Image:
    return solid((200, 30, 30))


def _g_solid_b() -> Image.Image:
    return solid((30, 200, 30))


def _g_solid_c() -> Image.Image:
    return solid((30, 30, 200))


def _g_gradient_1() -> Image.Image:
    return gradient(seed=1)


def _g_gradient_2() -> Image.Image:
    return gradient(seed=2)


def _g_gradient_3() -> Image.Image:
    return gradient(seed=3)


def _g_blob_alpha() -> Image.Image:
    return noisy_blob(seed=10, label="alpha")


def _g_blob_beta() -> Image.Image:
    return noisy_blob(seed=10, label="beta")


_GENERATORS = {
    "solid_a": _g_solid_a,
    "solid_b": _g_solid_b,
    "solid_c": _g_solid_c,
    "gradient_1": _g_gradient_1,
    "gradient_2": _g_gradient_2,
    "gradient_3": _g_gradient_3,
    "blob_alpha": _g_blob_alpha,
    "blob_beta": _g_blob_beta,
}


def available_generators() -> list[str]:
    return sorted(_GENERATORS)
