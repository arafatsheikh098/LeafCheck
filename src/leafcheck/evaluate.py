"""F4: evaluation entrypoint.

Run as `python -m leafcheck.evaluate --model-dir models --data-root <manifest.csv>`.

Produces:
- `models/threshold.json`
- `reports/eval.md` and `reports/confusion_matrix.png`
- `reports/eval.json` (machine-readable copy)

The threshold is selected on the **validation** split. The test split is
only ever read for the final metric reporting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display
import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image

from leafcheck import preprocess as pp
from leafcheck.metrics import (
    compute_metrics,
    confidence_bucket_accuracy,
    coverage_at_threshold,
    find_threshold,
    render_eval_markdown,
    robustness_table,
)
from leafcheck.model import build_model


def _load_class_names(model_dir: Path) -> list[str]:
    p = model_dir / "class_names.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing {p}. Train first with `python -m leafcheck.train`.")
    return json.loads(p.read_text())


def _load_model(model_dir: Path, num_classes: int) -> torch.nn.Module:
    model = build_model(num_classes, pretrained=False)
    state = torch.load(model_dir / "model.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    return model


def _read_manifest(manifest_path: Path) -> list[dict]:
    import csv

    out: list[dict] = []
    with manifest_path.open() as fh:
        for row in csv.DictReader(fh):
            out.append(row)
    return out


def _images_and_labels(
    rows: list[dict], split: str, class_to_idx: dict[str, int]
) -> tuple[list[Image.Image], list[int]]:
    images: list[Image.Image] = []
    labels: list[int] = []
    for row in rows:
        if row["split"] != split:
            continue
        try:
            img = Image.open(row["path"]).convert("RGB")
        except (OSError, ValueError):
            continue
        cls = row["class"]
        if cls not in class_to_idx:
            continue
        images.append(img)
        labels.append(class_to_idx[cls])
    return images, labels


def _predict_batch(
    model: torch.nn.Module,
    images: list[Image.Image],
    *,
    image_size: int,
) -> tuple[list[int], list[float]]:
    preds: list[int] = []
    confs: list[float] = []
    with torch.inference_mode():
        # Process in small batches to keep memory bounded.
        for start in range(0, len(images), 16):
            chunk = images[start : start + 16]
            x = pp.preprocess_batch(chunk, image_size=image_size, augment=False)
            logits = model(x)
            probs = torch.softmax(logits, dim=1)
            top_p, top_idx = probs.max(dim=1)
            preds.extend(top_idx.tolist())
            confs.extend(top_p.tolist())
    return preds, confs


def evaluate(model_dir: Path, manifest_path: Path, reports_dir: Path) -> dict:
    class_names = _load_class_names(model_dir)
    class_to_idx = {c: i for i, c in enumerate(class_names)}
    model = _load_model(model_dir, len(class_names))
    image_size = int(json.loads((model_dir / "metrics.json").read_text()).get("image_size", 224))

    rows = _read_manifest(manifest_path)

    val_images, val_labels = _images_and_labels(rows, "val", class_to_idx)
    test_images, test_labels = _images_and_labels(rows, "test", class_to_idx)
    if not val_images or not test_images:
        raise RuntimeError(
            f"Need both val and test images in the manifest; got "
            f"{len(val_images)} val and {len(test_images)} test"
        )

    # Validation: find threshold.
    val_preds, val_confs = _predict_batch(model, val_images, image_size=image_size)
    threshold = find_threshold(val_labels, val_preds, val_confs, target_precision=0.95)

    # Test: compute the headline metrics ONCE on the test split. Per F4.AC2
    # these are reproducible by re-running this command.
    test_preds, test_confs = _predict_batch(model, test_images, image_size=image_size)
    test_metrics = compute_metrics(test_labels, test_preds, class_names=class_names)
    test_coverage = coverage_at_threshold(test_confs, threshold.threshold)
    val_coverage = coverage_at_threshold(val_confs, threshold.threshold)
    confidence_buckets = confidence_bucket_accuracy(test_labels, test_preds, test_confs)

    # Robustness uses a downsized subset of test images so it stays fast.
    max_robust = min(32, len(test_images))
    rob = robustness_table(
        test_images[:max_robust],
        test_labels[:max_robust],
        predict_fn=lambda img: _predict_one(model, img, image_size=image_size),
        image_size=image_size,
    )

    # Write the threshold.
    threshold_dict = {
        "threshold": threshold.threshold,
        "target_precision": threshold.target_precision,
        "val_precision_at_threshold": threshold.val_precision_at_threshold,
        "val_coverage_at_threshold": threshold.val_coverage_at_threshold,
        "test_coverage_at_threshold": test_coverage,
    }
    (model_dir / "threshold.json").write_text(json.dumps(threshold_dict, indent=2))

    # Confusion matrix PNG.
    reports_dir.mkdir(parents=True, exist_ok=True)
    cm_png = reports_dir / "confusion_matrix.png"
    _plot_confusion_matrix(test_metrics["confusion_matrix"], class_names=class_names, out=cm_png)

    # Render markdown.
    md = render_eval_markdown(
        test_metrics=test_metrics,
        threshold=threshold,
        val_coverage=val_coverage,
        test_coverage=test_coverage,
        confidence_buckets=confidence_buckets,
        robustness=rob,
        class_names=class_names,
        confusion_matrix_png=cm_png,
    )
    (reports_dir / "eval.md").write_text(md)

    # Also write a machine-readable JSON for downstream tools.
    summary = {
        "accuracy": test_metrics["accuracy"],
        "macro_f1": test_metrics["macro_f1"],
        "threshold": threshold_dict,
        "per_class": test_metrics["per_class"],
        "robustness": rob,
        "confidence_buckets": confidence_buckets,
    }
    (reports_dir / "eval.json").write_text(json.dumps(summary, indent=2))
    return summary


def _predict_one(model: torch.nn.Module, img: Image.Image, *, image_size: int) -> tuple[int, float]:
    with torch.inference_mode():
        x = pp.preprocess_image(img, image_size=image_size).unsqueeze(0)
        logits = model(x)
        probs = torch.softmax(logits, dim=1)
        top_p, top_idx = probs.max(dim=1)
    return int(top_idx.item()), float(top_p.item())


def _plot_confusion_matrix(cm: list[list[int]], *, class_names: list[str], out: Path) -> None:
    arr = np.array(cm)
    fig, ax = plt.subplots(figsize=(max(6, len(class_names) * 0.4), max(5, len(class_names) * 0.4)))
    im = ax.imshow(arr, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(arr.shape[1]),
        yticks=np.arange(arr.shape[0]),
        xticklabels=class_names,
        yticklabels=class_names,
        ylabel="True label",
        xlabel="Predicted label",
        title="Confusion matrix (test split)",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(
                j,
                i,
                format(arr[i, j], "d"),
                ha="center",
                va="center",
                color="white" if arr[i, j] > arr.max() / 2 else "black",
            )
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="leafcheck.evaluate")
    p.add_argument("--model-dir", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path, help="manifest.csv from M2")
    p.add_argument(
        "--reports-dir", default=Path("reports"), type=Path, help="where to write eval.md"
    )
    p.add_argument("--config", type=Path, default=None, help="optional eval config")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = evaluate(args.model_dir, args.data_root, args.reports_dir)
    print(
        json.dumps(
            {
                "test_accuracy": summary["accuracy"],
                "test_macro_f1": summary["macro_f1"],
                "threshold": summary["threshold"]["threshold"],
                "test_coverage_at_threshold": summary["threshold"]["test_coverage_at_threshold"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
