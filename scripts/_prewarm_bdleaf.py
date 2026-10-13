"""Pre-resize all BdLeaf20 source images to a 768px JPEG cache.

Why: the source images are 4640x3472 PNGs (~5-8 MB each). The training
dataloader decodes them every epoch. Decoding that much PNG on CPU
dominates the epoch time, so we cache a 768px-long-side JPEG copy of
each image and rewrite the manifest to point at the cache.

This is a one-time cost (~30-60s for 429 images) and saves 5-10x per
epoch on the CPU training run.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

from PIL import Image

REPO = Path("/Users/arafatsheikh/D_Drive/github_project/project")
SRC_ROOT = Path.home() / "Downloads" / "BdLeaf20"
CACHE_ROOT = REPO / "data" / "bdleaf20_cache"
MANIFEST = REPO / "data" / "manifest.csv"
TARGET = 768  # px on the long side
JPEG_QUALITY = 88


def main() -> int:
    if CACHE_ROOT.exists():
        shutil.rmtree(CACHE_ROOT)
    CACHE_ROOT.mkdir(parents=True)

    rows = []
    with MANIFEST.open() as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        for row in reader:
            src = Path(row["path"])
            assert src.is_relative_to(SRC_ROOT), src
            rel = src.relative_to(SRC_ROOT)  # <class>/Sp06_Lf01.png
            dst = CACHE_ROOT / rel.with_suffix(".jpg")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                im = Image.open(src).convert("RGB")
                im.thumbnail((TARGET, TARGET), Image.BILINEAR)
                im.save(dst, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            row["path"] = str(dst)
            rows.append(row)

    # Write the rewritten manifest.
    with MANIFEST.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"rewrote {MANIFEST} to point at {CACHE_ROOT} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
