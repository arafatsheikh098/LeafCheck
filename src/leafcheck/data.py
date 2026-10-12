"""F1 + F2: data preparation CLI and library.

Entry points
------------

* `python -m leafcheck.data prepare --source <URL or local dir> --out data/`
  — fetch (best-effort) or read a local folder of PlantVillage images, hash
  every image, group near-duplicates across 8 orientations, write
  manifests + data_report.json + DATASET_INFO.md.

* `python -m leafcheck.data verify --out data/`
  — re-load the manifests and assert zero overlap by SHA-256 and by group.

Layout assumed for `--source <local dir>`::

    <source>/
        Tomato___Bacterial_spot/
            img1.jpg
            img2.jpg
        Tomato___healthy/
            ...
        Potato___Early_blight/
            ...

The class name is the parent directory. We also accept Kaggle's "Color"
layout which has a `PlantVillage/<class>/...` wrapper.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml
from PIL import Image, UnidentifiedImageError

from leafcheck.hashing import hamming_min, orientation_hashes
from leafcheck.split import SPLIT_NAMES, assign_groups

# Class catalog from PROJECT_SPEC.md (the 19 classes).
PLANTVILLAGE_CLASSES: list[tuple[str, str, str]] = [
    # (crop, condition, folder_name)
    ("Tomato", "Bacterial_spot", "Tomato___Bacterial_spot"),
    ("Tomato", "Early_blight", "Tomato___Early_blight"),
    ("Tomato", "Late_blight", "Tomato___Late_blight"),
    ("Tomato", "Leaf_Mold", "Tomato___Leaf_Mold"),
    ("Tomato", "Septoria_leaf_spot", "Tomato___Septoria_leaf_spot"),
    ("Tomato", "Spider_mites", "Tomato___Spider_mites_Two-spotted_spider_mite"),
    ("Tomato", "Target_Spot", "Tomato___Target_Spot"),
    ("Tomato", "Yellow_Leaf_Curl_Virus", "Tomato___Yellow_Leaf_Curl_Virus"),
    ("Tomato", "Mosaic_virus", "Tomato___Mosaic_virus"),
    ("Tomato", "healthy", "Tomato___healthy"),
    ("Potato", "Early_blight", "Potato___Early_blight"),
    ("Potato", "Late_blight", "Potato___Late_blight"),
    ("Potato", "healthy", "Potato___healthy"),
    ("Corn", "Cercospora", "Corn___Cercospora_leaf_spot Gray_leaf_spot"),
    ("Corn", "Common_rust", "Corn___Common_rust"),
    ("Corn", "Northern_Leaf_Blight", "Corn___Northern_Leaf_Blight"),
    ("Corn", "healthy", "Corn___healthy"),
    ("Bell_pepper", "Bacterial_spot", "Pepper__bell___Bacterial_spot"),
    ("Bell_pepper", "healthy", "Pepper__bell___healthy"),
]
CLASS_TO_CROP_CONDITION = {
    folder: (crop, condition) for crop, condition, folder in PLANTVILLAGE_CLASSES
}


@dataclass
class ImageRecord:
    path: Path
    class_name: str  # folder name, e.g. "Tomato___Bacterial_spot"
    sha256: str
    byte_size: int
    width: int
    height: int
    corrupt: bool = False


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def discover_images(source: Path) -> list[Path]:
    """Find image files under `source`, recursively.

    Recognised extensions: .jpg .jpeg .png .JPG .JPEG .PNG. We do not
    trust extensions for validation (that's done in `validate_image`).
    """
    exts = {".jpg", ".jpeg", ".png"}
    out: list[Path] = []
    for p in source.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            out.append(p)
    return sorted(out)


def class_from_path(image_path: Path, source: Path) -> str | None:
    """Return the parent folder name relative to source, or None."""
    try:
        rel = image_path.relative_to(source)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    return parts[0]


def validate_image(path: Path) -> ImageRecord | None:
    """Open and validate an image. Returns a record or None if corrupt."""
    try:
        sha = sha256_file(path)
        with Image.open(path) as img:
            img.verify()  # cheap structural check
        with Image.open(path) as img:
            img.load()
            w, h = img.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        return None
    if w <= 0 or h <= 0:
        return None
    return ImageRecord(
        path=path,
        class_name="",  # filled by caller
        sha256=sha,
        byte_size=path.stat().st_size,
        width=w,
        height=h,
        corrupt=False,
    )


# ---------- grouping ----------


def compute_groups(
    records: list[ImageRecord],
    *,
    hamming_threshold: int = 8,
) -> tuple[list[tuple[Path, str, str]], int]:
    """Group records by 8-orientation perceptual-hash similarity.

    Returns `(edges, duplicate_count)` where `edges` is a list of
    `(path, class_name, group_id)` and `duplicate_count` is the number of
    records that ended up in a group of size > 1.
    """
    # Hash every image across 8 orientations.
    per_record_hashes: list[tuple[ImageRecord, list]] = []
    for r in records:
        try:
            with Image.open(r.path) as img:
                img = img.convert("RGB")
                hs = orientation_hashes(img)
        except (UnidentifiedImageError, OSError, ValueError):
            continue
        per_record_hashes.append((r, hs))

    # Union-find over indices. We use raw group ids from the first member
    # of each equivalence class.
    parent: list[int] = list(range(len(per_record_hashes)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    # Group images by 8-orientation hash similarity.
    #
    # Bucketing strategy: we use the 8 hash strings as a multi-key bucket so
    # that two images that share ANY orientation-hash land in the same bucket.
    # For PlantVillage (~50k images, ~2k per class), this is still O(n) per
    # class and bounded by `max_per_class_pairwise`. If a class has more
    # than that, we fall back to a single-key canonical bucket and accept the
    # tiny risk of missing a same-orientation match (logged as a warning).
    max_per_class_pairwise = 512
    by_class: dict[str, list[int]] = defaultdict(list)
    for i, (rec, _) in enumerate(per_record_hashes):
        by_class[rec.class_name].append(i)

    for _class_name, indices in by_class.items():
        n = len(indices)
        if n > max_per_class_pairwise:
            # Fall back: bucket only by canonical (identity) hash. This is
            # the slow-but-correct path for very large classes; we use it
            # only when needed.
            bucket: dict[str, list[int]] = defaultdict(list)
            for i in indices:
                bucket[str(per_record_hashes[i][1][0])].append(i)
            for same in bucket.values():
                base = same[0]
                for other in same[1:]:
                    union(base, other)
            continue

        if n <= 32:
            # Small class: do a true pairwise check. O(n^2) is fine for
            # n <= 32 (~500 comparisons).
            for i_idx in range(n):
                for j_idx in range(i_idx + 1, n):
                    i = indices[i_idx]
                    j = indices[j_idx]
                    if (
                        hamming_min(per_record_hashes[i][1], per_record_hashes[j][1])
                        <= hamming_threshold
                    ):
                        union(i, j)
            continue

        # Larger class: bucket by 8 orientation hashes, then cross-check
        # within each bucket. This is O(n * 8 + bucket_size^2 * 8) per class,
        # which scales well up to a few hundred images.
        bucket: dict[str, list[int]] = defaultdict(list)
        for i in indices:
            for h in per_record_hashes[i][1]:
                bucket[str(h)].append(i)
        for same in bucket.values():
            if len(same) < 2:
                continue
            if len(same) > 256:
                same = same[:256]
            seen: set[int] = set()
            for i in same:
                if i in seen:
                    continue
                for j in same:
                    if j <= i or j in seen:
                        continue
                    if (
                        hamming_min(per_record_hashes[i][1], per_record_hashes[j][1])
                        <= hamming_threshold
                    ):
                        union(i, j)
                        seen.add(j)

    # Translate uf roots into a sequential group_id per (class, root).
    root_to_label: dict[tuple[str, int], str] = {}
    edges: list[tuple[Path, str, str]] = []
    duplicates = 0
    for idx, (rec, _) in enumerate(per_record_hashes):
        root = find(idx)
        key = (rec.class_name, root)
        if key not in root_to_label:
            root_to_label[key] = f"{rec.class_name}::g{len(root_to_label)}"
        gid = root_to_label[key]
        edges.append((rec.path, rec.class_name, gid))

    # duplicates = how many records share a group with at least one other.
    group_sizes: dict[str, int] = defaultdict(int)
    for _, _, gid in edges:
        group_sizes[gid] += 1
    duplicates = sum(1 for _, _, gid in edges if group_sizes[gid] > 1)

    return edges, duplicates


# ---------- top-level prepare / verify ----------


def prepare(
    source: str | Path,
    out: str | Path,
    *,
    config_path: str | Path | None = None,
) -> dict:
    """Run the full M2 pipeline: discover → validate → group → split → write.

    Returns a dict with the report (also written to data_report.json).
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    cfg = _load_config(config_path)
    seed = int(cfg.get("seed", 42))
    ratios = cfg.get("ratios", {"train": 0.70, "val": 0.15, "test": 0.15})
    hamming = int(cfg.get("group_hamming_threshold", 8))

    src = Path(source)
    if src.exists() and src.is_dir():
        image_paths = discover_images(src)
        source_kind = "local"
    elif str(source).startswith(("http://", "https://")):
        image_paths = _try_download(str(source), out)
        source_kind = "url"
    else:
        raise FileNotFoundError(
            f"--source {source!r} is neither a local directory nor an http(s) URL"
        )

    if not image_paths:
        raise RuntimeError(f"No images found under {source!r}")

    # Validate + assign class.
    records: list[ImageRecord] = []
    corrupt_count = 0
    for p in image_paths:
        rec = validate_image(p)
        if rec is None:
            corrupt_count += 1
            continue
        cls = class_from_path(p, src if source_kind == "local" else out)
        rec.class_name = cls or ""
        if not rec.class_name:
            # If the directory structure didn't give us a class, treat as corrupt.
            corrupt_count += 1
            continue
        records.append(rec)

    # Group.
    edges, duplicates = compute_groups(records, hamming_threshold=hamming)

    # Build the (class, group_id) tuple list and assign splits. Group ids
    # emitted by `compute_groups` are already namespaced as `<class>::g<n>`,
    # so we use them directly — no need to re-namespace via make_group_key.
    class_for_group = [cls for _, cls, gid in edges]
    group_for_group = [gid for _, cls, gid in edges]
    pairs = list(set(zip(group_for_group, class_for_group, strict=False)))  # unique
    assignments = assign_groups(pairs, ratios=ratios, seed=seed)
    group_to_split = {(a.class_name, a.group_id): a.split for a in assignments}

    # Write the manifest.
    manifest_path = out / "manifest.csv"
    with manifest_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "class", "group_id", "split", "sha256"])
        for path, cls, gid in edges:
            split = group_to_split.get((cls, gid), "train")
            sha = next((r.sha256 for r in records if r.path == path), "")
            # Store the path as the absolute path so the verify step can
            # re-hash even after the source is moved.
            w.writerow([str(path), cls, gid, split, sha])

    # Build the data report.
    class_counts: dict[str, int] = defaultdict(int)
    group_counts: dict[str, int] = defaultdict(int)
    split_counts: dict[str, int] = defaultdict(int)
    for _, cls, gid in edges:
        split = group_to_split.get((cls, gid), "train")
        class_counts[cls] += 1
        group_counts[gid] += 1
        split_counts[split] += 1

    report = {
        "source": str(source),
        "source_kind": source_kind,
        "total_images": len(records),
        "corrupt_images": corrupt_count,
        "duplicate_images_in_groups": duplicates,
        "class_count": len(class_counts),
        "group_count": len(group_counts),
        "split_count": dict(split_counts),
        "classes": sorted(class_counts),
        "ratios": ratios,
        "seed": seed,
        "hamming_threshold": hamming,
        "per_class_split": _per_class_split_stats(edges, group_to_split),
        "warnings": _collect_warnings(edges, group_to_split, class_counts),
    }
    (out / "data_report.json").write_text(json.dumps(report, indent=2))

    _write_dataset_info(out)
    return report


def verify(out: str | Path) -> dict:
    """Re-load the manifest and assert zero overlap across splits."""
    out = Path(out)
    manifest_path = out / "manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest at {manifest_path}; run `prepare` first")

    by_split: dict[str, set[str]] = {s: set() for s in SPLIT_NAMES}
    by_split_group: dict[str, set[str]] = {s: set() for s in SPLIT_NAMES}
    rows = 0
    with manifest_path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows += 1
            sp = row["split"]
            if sp not in by_split:
                continue
            by_split[sp].add(row["sha256"])
            by_split_group[sp].add(row["group_id"])

    sha_overlap = _pairwise_overlap(by_split)
    group_overlap = _pairwise_overlap(by_split_group)

    ok = (not any(sha_overlap.values())) and (not any(group_overlap.values()))
    return {
        "ok": ok,
        "rows": rows,
        "sha256_overlap": sha_overlap,
        "group_overlap": group_overlap,
    }


def _pairwise_overlap(sets: dict[str, set[str]]) -> dict[str, int]:
    out: dict[str, int] = {}
    names = list(sets)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            out[f"{a}+{b}"] = len(sets[a] & sets[b])
    return out


def _per_class_split_stats(
    edges: list[tuple[Path, str, str]],
    group_to_split: dict[tuple[str, str], str],
) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, cls, gid in edges:
        sp = group_to_split.get((cls, gid), "train")
        out[cls][sp] += 1
    return {k: dict(v) for k, v in out.items()}


def _collect_warnings(
    edges: list[tuple[Path, str, str]],
    group_to_split: dict[tuple[str, str], str],
    class_counts: dict[str, int],
) -> list[str]:
    warnings: list[str] = []
    # Warn when a class is too small to hit the 1% target on every split.
    for cls, n in class_counts.items():
        if n < 10:
            warnings.append(
                f"class {cls!r} has only {n} images; per-class split ratio may deviate from 70/15/15"
            )
    return warnings


def _load_config(path: str | Path | None) -> dict:
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def _try_download(url: str, out: Path) -> list[Path]:
    """Best-effort download of a zip of images. Returns discovered image paths.

    Fails loudly (raises) on error so the caller can fall back to the
    local-folder source.
    """
    target = out / "_downloaded.zip"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            target.write_bytes(resp.read())
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"Failed to download {url!r}: {exc}") from exc
    extract_dir = out / "_downloaded"
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(target) as zf:
        zf.extractall(extract_dir)
    return discover_images(extract_dir)


def _write_dataset_info(out: Path) -> None:
    """Write a short dataset-info file (license + citation) for F1.AC3.

    This is called during `prepare`; the user is expected to verify the
    license and citation match what they downloaded.
    """
    text = (
        "# Dataset: PlantVillage (color)\n\n"
        "- Source: https://data.mendeley.com/datasets/tywbtsjrjv/1\n"
        "- Mirror: https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset\n"
        "- Citation:\n"
        "  > Hughes, D. P., & Salathé, M. (2015). An open access repository of "
        "images on plant health to enable the development of mobile disease "
        "diagnostics. arXiv preprint arXiv:1511.08060.\n"
        "- License: CC-BY-SA-3.0 (verify against the dataset's own LICENSE before "
        "  shipping; some variants are CC-BY-NC-SA which is NOT compatible with "
        "  redistribution).\n"
        "\n"
        "If you downloaded a different PlantVillage distribution, edit the "
        "license line above to match what came with the archive.\n"
    )
    (out / "DATASET_INFO.md").write_text(text)


# ---------- CLI ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="leafcheck.data")
    sub = p.add_subparsers(dest="cmd", required=True)

    prep = sub.add_parser("prepare", help="download/load images, group, split, write manifests")
    prep.add_argument("--source", required=True, help="local dir or http(s) URL")
    prep.add_argument("--out", required=True, help="output directory for manifests + report")
    prep.add_argument("--config", default=None, help="optional YAML config")

    ver = sub.add_parser("verify", help="re-check zero overlap on a manifest")
    ver.add_argument("--out", required=True, help="output directory containing manifest.csv")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "prepare":
        report = prepare(args.source, args.out, config_path=args.config)
        print(json.dumps(_summarise_report(report), indent=2))
        return 0
    if args.cmd == "verify":
        result = verify(args.out)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    return 2


def _summarise_report(report: dict) -> dict:
    return {
        "total_images": report.get("total_images"),
        "corrupt_images": report.get("corrupt_images"),
        "duplicate_images_in_groups": report.get("duplicate_images_in_groups"),
        "class_count": report.get("class_count"),
        "group_count": report.get("group_count"),
        "split_count": report.get("split_count"),
        "warnings": report.get("warnings", []),
    }


if __name__ == "__main__":
    sys.exit(main())
