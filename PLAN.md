# PLAN.md — milestones, files, and tests

> Companion to SCOPE.md. Milestone names match PROJECT_SPEC.md exactly.
> Each milestone lists the files it will create and the tests it must add.

---

## M1 — Foundation
**Goal:** A clean virtualenv can install the package, lint passes, tests pass, `GET /health` returns 200, and the Docker image builds.

**Files this milestone creates:**
- `pyproject.toml` (Python 3.11+, pinned CPU-only torch/torchvision, ruff config, pytest config)
- `src/leafcheck/__init__.py`
- `src/leafcheck/app/main.py` (FastAPI app factory with `GET /health`)
- `src/leafcheck/app/__init__.py`
- `tests/unit/test_health.py` (`TestClient` hits `/health`, asserts 200)
- `Makefile` (targets: `setup`, `lint`, `test`, `train-smoke`, `run`)
- `Dockerfile` (CPU torch wheels, non-root, `python -m uvicorn` entrypoint)
- `.dockerignore`
- `.gitignore` (data/, large artifacts ignored; models/ tracked)
- `.github/workflows/ci.yml` (lint + tests job)
- `pytest.ini` (or equivalent in `pyproject.toml`) — sets `testpaths = tests`
- `ruff.toml` (or equivalent in `pyproject.toml`) — line length + rules

**Tests this milestone adds:**
- `tests/unit/test_health.py` — health endpoint returns 200 and `{"status": "ok"}` JSON.

**Acceptance evidence (from SCOPE.md):** `pip install -e .[dev]` succeeds; `pytest` green; `docker build` succeeds; image size recorded in `DECISIONS.md`.

---

## M2 — Data pipeline and leakage-safe split
**Goal:** `python -m leafcheck.data prepare --source <URL or local dir> --out data/` produces a leakage-safe split on real PlantVillage images (or documents the manual download path), and a synthetic test proves planted rotated/flipped copies stay together.

**Files this milestone creates:**
- `src/leafcheck/data.py` — `prepare(source, out)` CLI; downloader with local-folder fallback; image validator; SHA-256 + perceptual-hash computer (all 8 orientations).
- `src/leafcheck/hashing.py` — perceptual-hash helpers, group-by-orientation-match.
- `src/leafcheck/split.py` — group-aware stratified split; manifest writer.
- `configs/data.yaml` — paths, seed, ratios, hamming threshold.
- `src/leafcheck/synth_data.py` — synthetic-image generator for tests (solid-color images, deterministic).
- `tests/unit/test_hashing.py` — orientation-match, exact-duplicate, near-duplicate grouping.
- `tests/unit/test_split.py` — proportions, group-disjointness, target-column absence.
- `tests/integration/test_data_pipeline.py` — end-to-end prepare on a synthetic set; corrupt-image handling.
- `data/.gitkeep` (data is gitignored; placeholder only)
- `data/DATASET_INFO.md` template / generated when the real source is reachable.

**Tests this milestone adds:**
- `tests/unit/test_hashing.py`
- `tests/unit/test_split.py`
- `tests/integration/test_data_pipeline.py`

**Acceptance evidence (from SCOPE.md):** F1.AC1, F1.AC2, F1.AC4, F2.AC1, F2.AC2, F2.AC3, F2.AC4 verified by running the tests + the verify command.

---

## M3 — Training
**Goal:** `python -m leafcheck.train --config configs/train.yaml` trains a MobileNetV3-Small and writes `models/model.pt`, `class_names.json`, `metrics.json`, plus a config snapshot. A CI smoke config runs in <2 min on a tiny synthetic set.

**Files this milestone creates:**
- `src/leafcheck/train.py` — training entrypoint.
- `src/leafcheck/model.py` — MobileNetV3-Small builder (ImageNet-pretrained, num_classes from manifest).
- `src/leafcheck/preprocess.py` — **shared** preprocessing (used by training, evaluation, and serving — see G2).
- `configs/train.yaml` — full training config.
- `configs/smoke.yaml` — tiny CI-sized config.
- `scripts/train_full.sh` — documented to run on a GPU machine.
- `models/.gitkeep` (real artifacts land in M4; models/ is committed with a small budget — see M7)
- `tests/unit/test_train.py` — seed determinism, BatchNorm-eval-mode invariance, imbalance-flag, smoke training finishes in <2 min on synthetic.
- `tests/unit/test_preprocess_shared.py` — training, evaluation, and serving all import the same `preprocess` function (G2).

**Tests this milestone adds:**
- `tests/unit/test_train.py`
- `tests/unit/test_preprocess_shared.py`

**Acceptance evidence (from SCOPE.md):** F3.AC1, F3.AC2, F3.AC3, F3.AC4, F3.AC5.

---

## M4 — Evaluation and threshold
**Goal:** `python -m leafcheck.evaluate` produces `reports/eval.md` with the confusion matrix, per-class table, confidence-bucket table, robustness table, the chosen threshold, and the coverage at that threshold. `threshold.json` is saved next to the model.

**Files this milestone creates:**
- `src/leafcheck/evaluate.py` — evaluation entrypoint.
- `src/leafcheck/metrics.py` — accuracy, macro-F1, per-class P/R/F1, confidence-bucket accuracy, robustness table helpers.
- `src/leafcheck/threshold.py` — validation-only threshold selector.
- `reports/.gitkeep`
- `configs/eval.yaml` — eval config (precision target, robustness parameters).
- `tests/unit/test_evaluate.py` — metrics correctness on a tiny synthetic test split.
- `tests/unit/test_threshold.py` — threshold selected from val only; test split is never read during selection.
- `tests/unit/test_robustness.py` — robustness helpers produce expected columns.

**Tests this milestone adds:**
- `tests/unit/test_evaluate.py`
- `tests/unit/test_threshold.py`
- `tests/unit/test_robustness.py`

**Acceptance evidence (from SCOPE.md):** F4.AC1, F4.AC2, F4.AC3, F4.AC4, F4.AC5.

---

## M5 — Inference API
**Goal:** FastAPI serves `/api/predict`, `/api/classes`, `/api/model-info`, `/health` with the shared preprocessing module, the validation-tuned threshold, and a startup-time model load.

**Files this milestone creates:**
- `src/leafcheck/api/predict.py` — `POST /api/predict` route.
- `src/leafcheck/api/meta.py` — `GET /api/classes`, `GET /api/model-info`, `GET /health`.
- `src/leafcheck/api/schemas.py` — Pydantic response models.
- `src/leafcheck/api/dependencies.py` — model loader, threshold loader, advice loader.
- `src/leafcheck/validate.py` — content-based image validation (max 5 MB, JPEG/PNG/WebP, pixel-count cap, decompression-bomb guard, EXIF rotation, RGB convert).
- `src/leafcheck/predictor.py` — `Predictor` class: load model once, predict with `torch.inference_mode`, apply threshold, build response.
- `tests/unit/test_validate.py` — all rejection cases from F5.AC1.
- `tests/unit/test_predictor.py` — not_sure logic with mocked logits.
- `tests/integration/test_api.py` — full API: parallel requests, health reports model_loaded, startup fails on missing files / class-count mismatch.
- `src/leafcheck/main.py` (or extend `src/leafcheck/app/main.py` from M1) — wire the routes.

**Tests this milestone adds:**
- `tests/unit/test_validate.py`
- `tests/unit/test_predictor.py`
- `tests/integration/test_api.py`

**Acceptance evidence (from SCOPE.md):** F5.AC1–F5.AC6.

---

## M6 — Frontend and advice
**Goal:** A mobile-first vanilla HTML/JS page uploads/captures a leaf photo, downscales to ≤1024px, posts to `/api/predict`, shows the result with confidence bars, toggles EN/Bangla (persisted in localStorage), and renders the "not sure" and error states. `data/advice.json` covers all 19 classes in both languages.

**Files this milestone creates:**
- `src/leafcheck/static/index.html`
- `src/leafcheck/static/styles.css`
- `src/leafcheck/static/app.js` (vanilla JS, no CDN)
- `src/leafcheck/static/i18n.js` (EN/Bangla strings)
- `src/leafcheck/advice.py` — loads `data/advice.json`, surfaces per-class advice in the API response.
- `data/advice.json` — entries for all 19 classes (en, bn, reviewed_by_human=false).
- `tests/unit/test_advice.py` — schema test (F7.AC1) and guard test (F7.AC2).
- `tests/e2e/test_frontend.py` — Playwright: upload example, see result, toggle Bangla, see mocked not_sure, see error for bad file, assert zero console errors, no horizontal scroll at 375px, no external hosts.
- `tests/conftest.py` — Playwright fixtures, dev-server fixture.

**Tests this milestone adds:**
- `tests/unit/test_advice.py`
- `tests/e2e/test_frontend.py`

**Acceptance evidence (from SCOPE.md):** F6.AC1–F6.AC6, F7.AC1–F7.AC3.

---

## M7 — Deployment package and examples
**Goal:** `docker run` serves the UI; one prediction per `examples/` image returns the expected class; the image builds from a clean clone; peak memory and cold-start are measured.

**Files this milestone creates:**
- `examples/` — 6 hand-picked images with `examples/labels.json` (filename → expected class). Documented as hand-picked in `examples/README.md`.
- `scripts/smoke_test.sh` — runs `GET /health`, `GET /api/classes`, one `/api/predict` per example, one rejected upload; non-zero exit on any failure.
- `Dockerfile` — final CPU torch, non-root, `HEALTHCHECK`, small image.
- `.dockerignore`
- `tests/integration/test_examples.py` — hits the real API for each `examples/` file and asserts the expected class (G5).
- `tests/integration/test_smoke_script.py` — runs `scripts/smoke_test.sh` against a local container / dev server.
- `scripts/measure_memory.sh` — measures peak inference memory; result written into README during the README phase (R), but the measurement happens here.
- `docs/bench.md` placeholder; the final README (phase R) is what records the numbers.

**Tests this milestone adds:**
- `tests/integration/test_examples.py`
- `tests/integration/test_smoke_script.py`

**Acceptance evidence (from SCOPE.md):** F8.AC1–F8.AC5, G5, G6.
