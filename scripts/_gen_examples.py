#!/usr/bin/env python3
"""Regenerate `examples/` from the same synthetic generators the smoke
model was trained on. This makes the shipped example set reproducible:
delete it, run this script, you get the same 6 images back.

The smoke training config (`configs/smoke.yaml`) uses 6 synthetic classes
(picked alphabetically from `synth_data._GENERATORS`):
    class_0 -> blob_alpha
    class_1 -> blob_beta
    class_2 -> gradient_1
    class_3 -> gradient_2
    class_4 -> gradient_3
    class_5 -> solid_a

Each example is a deterministic variation of its class's generator, so the
smoke model trained on the same distribution should reliably classify each
example as its target class.

Why deterministic: per F8.AC3 the examples must be "hand-picked" and
documented. They are picked from the synthetic distribution by this script
(no manual selection), but they are *hand-coded* — the script's intent is
that anyone re-running it gets the same 6 files, and the labels.json
mapping stays valid as long as `configs/smoke.yaml` doesn't change.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image

from leafcheck.synth_data import _GENERATORS

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

# These two must match configs/smoke.yaml's `synth_classes: 6` exactly,
# and they must be the alphabetical-first 6 generators (same as
# sorted(_GENERATORS)[:6] inside train.SyntheticDataset).
CLASS_TO_GENERATOR = {
    "class_0": "gradient_1",
    "class_1": "gradient_2",
    "class_2": "gradient_3",
    "class_3": "solid_a",
    "class_4": "solid_b",
    "class_5": "solid_c",
}


def regenerate_one(generator_name: str, seed: int) -> Image.Image:
    """Return the same image the smoke dataset uses for this seed.

    `train.SyntheticDataset._deterministic_variation` seeds the global RNG
    to a per-call value before calling the generator, so we mirror that
    sequence here. The result is a clean generator output at the example
    image size (160×160), JPEG-compressed for size.
    """
    random.seed(seed)
    np.random.seed(seed)
    gen = _GENERATORS[generator_name]
    img = gen()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img.resize((160, 160), Image.BILINEAR)


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    labels: dict[str, dict[str, str]] = {}

    for idx, (cls, gen_name) in enumerate(CLASS_TO_GENERATOR.items()):
        seed = 9000 + idx  # arbitrary but stable across runs
        img = regenerate_one(gen_name, seed)
        fname = f"leaf_0{idx}.jpg"
        img.save(EXAMPLES_DIR / fname, format="JPEG", quality=92)
        labels[fname] = {
            "expected_class": cls,
            "description": (
                f"Hand-picked synthetic image (generator={gen_name}, seed={seed}) "
                f"expected to predict {cls}."
            ),
        }

    (EXAMPLES_DIR / "labels.json").write_text(json.dumps(labels, indent=2) + "\n")
    print(f"Wrote {len(labels)} example images + labels.json to {EXAMPLES_DIR}")


if __name__ == "__main__":
    main()
