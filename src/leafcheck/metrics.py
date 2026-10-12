"""F4: metrics + threshold + robustness helpers.

All evaluation metrics (accuracy, macro-F1, per-class P/R/F1, confidence-
bucket accuracy, robustness tables) live here. The CLI in `evaluate.py`
uses these helpers to write `reports/eval.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)


@dataclass
class ThresholdResult:
    """Result of the validation-only "not sure" threshold search.

    `threshold` is the smallest confidence c such that on the validation
    set, predictions accepted with conf >= c achieve precision >= the
    configured `target_precision` (default 0.95).
    """

    threshold: float
    target_precision: float
    val_precision_at_threshold: float
    val_coverage_at_threshold: float
    test_coverage_at_threshold: float  # populated after re-applying to test


def _apply_perturbation(
    img: Image.Image,
    *,
    blur_radius: int = 0,
    brightness: float = 1.0,
    contrast: float = 1.0,
    jpeg_quality: int = 95,
    small_rotation_deg: float = 0.0,
    center_crop_frac: float = 1.0,
) -> Image.Image:
    """Apply a synthetic perturbation to a PIL image (for robustness table)."""
    from io import BytesIO

    if blur_radius > 0:
        from PIL import ImageFilter

        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    if brightness != 1.0 or contrast != 1.0:
        from PIL import ImageEnhance

        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if small_rotation_deg != 0.0:
        img = img.rotate(small_rotation_deg, resample=Image.BILINEAR, expand=False)
    if center_crop_frac < 1.0:
        w, h = img.size
        cw, ch = int(w * center_crop_frac), int(h * center_crop_frac)
        left = (w - cw) // 2
        top = (h - ch) // 2
        img = img.crop((left, top, left + cw, top + ch)).resize((w, h), Image.BILINEAR)
    if jpeg_quality < 95:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=jpeg_quality)
        buf.seek(0)
        img = Image.open(buf).copy()
    return img


def compute_metrics(
    labels: list[int],
    preds: list[int],
    *,
    class_names: list[str],
) -> dict:
    """Accuracy, macro-F1, per-class P/R/F1, confusion matrix, classification report."""
    acc = float(accuracy_score(labels, preds))
    macro_f1 = float(f1_score(labels, preds, average="macro", zero_division=0))
    p, r, f, supp = precision_recall_fscore_support(
        labels, preds, labels=list(range(len(class_names))), zero_division=0
    )
    cm = confusion_matrix(labels, preds, labels=list(range(len(class_names))))
    report = classification_report(
        labels, preds, target_names=class_names, output_dict=True, zero_division=0
    )
    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class": [
            {
                "class": class_names[i],
                "precision": float(p[i]),
                "recall": float(r[i]),
                "f1": float(f[i]),
                "support": int(supp[i]),
            }
            for i in range(len(class_names))
        ],
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }


def confidence_bucket_accuracy(
    labels: list[int],
    preds: list[int],
    confidences: list[float],
    *,
    bucket_edges: list[float] | None = None,
) -> list[dict]:
    """Accuracy bucketed by model confidence. Buckets: [0,.5), [.5,.8), [.8,.95), [.95,1]."""
    if bucket_edges is None:
        bucket_edges = [0.0, 0.5, 0.8, 0.95, 1.0001]
    buckets: list[dict] = []
    for i in range(len(bucket_edges) - 1):
        lo, hi = bucket_edges[i], bucket_edges[i + 1]
        indices = [j for j, c in enumerate(confidences) if lo <= c < hi]
        if not indices:
            buckets.append(
                {
                    "lo": lo,
                    "hi": hi,
                    "n": 0,
                    "accuracy": None,
                }
            )
            continue
        correct = sum(int(preds[j] == labels[j]) for j in indices)
        buckets.append(
            {
                "lo": lo,
                "hi": hi,
                "n": len(indices),
                "accuracy": correct / len(indices),
            }
        )
    return buckets


def find_threshold(
    val_labels: list[int],
    val_preds: list[int],
    val_confidences: list[float],
    *,
    target_precision: float = 0.95,
) -> ThresholdResult:
    """Find the smallest confidence threshold whose precision is >= target.

    Walks candidate thresholds in 0.01 increments and picks the smallest
    that meets the precision target on the validation set.
    """
    candidates = [round(c, 2) for c in np.arange(0.0, 1.0001, 0.01).tolist()]
    chosen = 0.0
    chosen_precision = 0.0
    chosen_coverage = 0.0
    for t in candidates:
        accepted = [i for i, c in enumerate(val_confidences) if c >= t]
        if not accepted:
            continue
        correct = sum(int(val_preds[i] == val_labels[i]) for i in accepted)
        precision = correct / len(accepted)
        coverage = len(accepted) / len(val_labels)
        if precision >= target_precision:
            chosen = t
            chosen_precision = precision
            chosen_coverage = coverage
            break
    return ThresholdResult(
        threshold=chosen,
        target_precision=target_precision,
        val_precision_at_threshold=chosen_precision,
        val_coverage_at_threshold=chosen_coverage,
        test_coverage_at_threshold=0.0,  # filled by caller
    )


def coverage_at_threshold(confidences: list[float], threshold: float) -> float:
    """Fraction of confidences >= threshold."""
    if not confidences:
        return 0.0
    n = sum(1 for c in confidences if c >= threshold)
    return n / len(confidences)


def robustness_table(
    images: list[Image.Image],
    labels: list[int],
    *,
    predict_fn,
    image_size: int = 224,
) -> list[dict]:
    """Apply each synthetic perturbation and measure accuracy.

    `predict_fn(img)` must return (pred_label, confidence).
    """

    perturbations: list[dict] = [
        {"name": "baseline", "kwargs": {}},
        {"name": "blur_r2", "kwargs": {"blur_radius": 2}},
        {"name": "blur_r4", "kwargs": {"blur_radius": 4}},
        {"name": "bright_1.2", "kwargs": {"brightness": 1.2}},
        {"name": "bright_0.8", "kwargs": {"brightness": 0.8}},
        {"name": "contrast_1.2", "kwargs": {"contrast": 1.2}},
        {"name": "contrast_0.8", "kwargs": {"contrast": 0.8}},
        {"name": "jpeg_50", "kwargs": {"jpeg_quality": 50}},
        {"name": "jpeg_20", "kwargs": {"jpeg_quality": 20}},
        {"name": "rot_5", "kwargs": {"small_rotation_deg": 5.0}},
        {"name": "rot_neg_5", "kwargs": {"small_rotation_deg": -5.0}},
        {"name": "center_crop_0.8", "kwargs": {"center_crop_frac": 0.8}},
    ]
    rows: list[dict] = []
    for p in perturbations:
        preds: list[int] = []
        for img in images:
            perturbed = _apply_perturbation(img, **p["kwargs"])
            pred, _conf = predict_fn(perturbed)
            preds.append(pred)
        acc = float(accuracy_score(labels, preds))
        rows.append({"perturbation": p["name"], "accuracy": acc, "n": len(images)})
    return rows


def render_eval_markdown(
    *,
    test_metrics: dict,
    threshold: ThresholdResult,
    val_coverage: float,
    test_coverage: float,
    confidence_buckets: list[dict],
    robustness: list[dict],
    class_names: list[str],
    confusion_matrix_png: Path | None,
) -> str:
    """Render the auto-generated reports/eval.md.

    All numbers come from the inputs (which are themselves generated from
    the test split) — no numbers are typed by hand (F4.AC4).
    """
    lines: list[str] = []
    lines.append("# LeafCheck — evaluation report")
    lines.append("")
    lines.append("> Auto-generated by `python -m leafcheck.evaluate`. Do not edit by hand.")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(f"- Test accuracy: **{test_metrics['accuracy']:.4f}**")
    lines.append(f"- Test macro-F1: **{test_metrics['macro_f1']:.4f}**")
    lines.append(
        f'- "Not sure" threshold: **{threshold.threshold:.2f}** '
        f"(validation precision at threshold: "
        f"{threshold.val_precision_at_threshold:.4f}, "
        f"target: {threshold.target_precision:.2f})"
    )
    lines.append(f"- Test coverage at threshold: **{test_coverage:.4f}**")
    lines.append(f"- Validation coverage at threshold: **{val_coverage:.4f}**")
    lines.append("")
    lines.append("## Per-class metrics")
    lines.append("")
    lines.append("| class | precision | recall | f1 | support |")
    lines.append("|---|---|---|---|---|")
    for row in test_metrics["per_class"]:
        lines.append(
            f"| {row['class']} | {row['precision']:.4f} | {row['recall']:.4f} | "
            f"{row['f1']:.4f} | {row['support']} |"
        )
    lines.append("")
    lines.append("## Confidence-bucket accuracy (test split)")
    lines.append("")
    lines.append("| bucket | n | accuracy |")
    lines.append("|---|---|---|")
    for b in confidence_buckets:
        acc = "—" if b["accuracy"] is None else f"{b['accuracy']:.4f}"
        lines.append(f"| [{b['lo']:.2f}, {b['hi']:.2f}) | {b['n']} | {acc} |")
    lines.append("")
    lines.append("## Robustness (test split)")
    lines.append("")
    lines.append("| perturbation | accuracy | n |")
    lines.append("|---|---|---|")
    for row in robustness:
        lines.append(f"| {row['perturbation']} | {row['accuracy']:.4f} | {row['n']} |")
    lines.append("")
    if confusion_matrix_png is not None and confusion_matrix_png.exists():
        lines.append("## Confusion matrix")
        lines.append("")
        lines.append(f"![confusion matrix]({confusion_matrix_png.name})")
        lines.append("")
    lines.append("## Limitations (plain language)")
    lines.append("")
    lines.append(
        "These numbers are reported on the **test split** of the PlantVillage "
        '"color" images, which are lab-style photos taken against a plain '
        "background with a single leaf in frame. Real field photos — uneven "
        "lighting, occluded leaves, multiple diseases, dirt, water droplets — "
        "will look very different and the model's accuracy will be lower. The "
        "confidence-bucket table and the robustness table are honest attempts "
        "to show how brittle the model is, not just how good it is on lab data."
    )
    lines.append("")
    return "\n".join(lines)
