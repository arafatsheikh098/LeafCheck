# FINAL_REPORT.md

Final scope audit. Maps every acceptance criterion in [`SCOPE.md`](SCOPE.md) to
the test, command, or artifact that demonstrates it, and records the
out-of-scope items that were deliberately not built.

## Status summary

| Phase         | Status | Evidence                                                            |
| ------------- | ------ | ------------------------------------------------------------------- |
| M1 Foundation | done   | branch `m1-foundation` merged; project boots, `/health` 200, lint green |
| M2 Data       | done   | branch `m2-data-pipeline` merged; CLI ships; verify subcommand green |
| M3 Training   | done   | branch `m3-training` merged; 73/73 unit+integration green            |
| M4 Evaluation | done   | branch `m4-evaluation` merged; `reports/eval.md` auto-generated      |
| M5 Inference  | done   | branch `m5-inference-api` merged; F5.AC1–6 covered                  |
| M6 Frontend   | done   | branch `m6-frontend-advice` merged; 6/6 e2e Playwright green        |
| M7 Deploy     | done   | branch `m7-deployment-examples` merged; 6/6 examples, Docker 1.47 GB |
| H Hardening   | done   | branch `h-hardening` merged; 3× test runs all green                 |
| F Fresh clone | done   | branch `f-fresh-clone` merged; both Docker and dev paths green       |
| D Deployment  | done   | branch `d-deployment-prep` merged; `DEPLOY.md` + `SPACE_README.md`   |
| R Final README| done   | branch `r-final-readme` merged; full quick-start, API, perf, arch   |
| X This report | done   | you're reading it                                                   |

Final test count: **74 unit/integration** + **6 e2e** = **80 passing** (1 deterministic skip in `test_split.py::test_different_seeds_can_differ`).

---

## F1 — Data pipeline CLI

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F1.AC1  | `tests/integration/test_data_pipeline.py::test_prepare_writes_manifest_with_sha256`                       | PASS   |
| F1.AC2  | `tests/integration/test_data_pipeline.py::test_prepare_handles_corrupt_images`                            | PASS   |
| F1.AC3  | `data/DATASET_INFO.md` exists with license (CC-BY-SA 3.0) and citation; covered by `test_dataset_info_written` | PASS   |
| F1.AC4  | `python -m leafcheck.data prepare --source <local dir>` (and `--source <URL>`) — both code paths exist and are exercised by `test_prepare_writes_manifest_with_sha256` and a unit test for the URL fallback. | PASS |

CLI: `python -m leafcheck.data prepare --source <dir> --out data/`.

## F2 — Leakage-safe split

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F2.AC1  | `tests/integration/test_data_pipeline.py::test_group_assignment_is_leak_free` plants exact dups, near-dups, rotations, and flips. | PASS |
| F2.AC2  | `tests/integration/test_data_pipeline.py::test_per_class_split_within_one_percent` and `tests/unit/test_split.py::test_assign_groups_within_one_percent_per_class`. | PASS |
| F2.AC3  | `tests/integration/test_data_pipeline.py::test_verify_reports_zero_overlap`; CLI: `python -m leafcheck.data verify --out data/`. | PASS |
| F2.AC4  | Manifests are CSV with `path,class,group_id,split,sha256` columns — see `data.py::write_manifest` and `data/manifests/manifest.csv` schema in the integration test fixtures. | PASS |

## F3 — Training

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F3.AC1  | `tests/unit/test_train.py::test_seed_determinism` runs the smoke training twice with the same seed and asserts metric parity. | PASS |
| F3.AC2  | `tests/unit/test_train.py::test_saved_artifacts_load_and_predict` loads `model.pt`, `class_names.json`, `metrics.json`, config snapshot from disk. | PASS |
| F3.AC3  | `tests/unit/test_train.py::test_batchnorm_is_in_eval_mode_at_inference` proves batched-vs-single inference parity. | PASS |
| F3.AC4  | `tests/unit/test_train.py::test_smoke_training_finishes_under_two_minutes` (CI config).                  | PASS |
| F3.AC5  | `tests/unit/test_train.py::test_class_imbalance_threshold_uses_weighted_loss` and `...below_threshold_does_not_use_weighted_loss`. | PASS |

## F4 — Evaluation and threshold

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F4.AC1  | `tests/unit/test_evaluate.py::test_find_threshold_uses_validation_only` and `test_evaluate_end_to_end_uses_only_val_for_threshold`. | PASS |
| F4.AC2  | `tests/integration/test_data_pipeline.py` (evaluation invoked via `python -m leafcheck.evaluate`); unit tests cover accuracy, macro-F1, per-class P/R/F1, confusion matrix, confidence buckets. | PASS |
| F4.AC3  | `tests/unit/test_evaluate.py::test_eval_md_has_no_typed_numbers` asserts the report has the threshold, coverage, and limitations sections in `reports/eval.md`. | PASS |
| F4.AC4  | `tests/unit/test_evaluate.py::test_robustness_table_runs_and_returns_rows` checks the 6-column robustness table. | PASS |
| F4.AC5  | `models/threshold.json` is present and `tests/integration/test_api.py::test_model_info_endpoint` confirms the API reads it. | PASS |

## F5 — Inference API

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F5.AC1  | `tests/unit/test_validate.py`: 11 tests covering EXIF-rotated JPEG, RGBA PNG, grayscale, WebP, truncated JPEG, oversize, text-renamed-jpg, empty, huge-pixel-count. | PASS |
| F5.AC2  | `tests/unit/test_predictor.py::test_predictor_threshold_below_marks_not_sure` and `..._above_does_not_mark_not_sure`. | PASS |
| F5.AC3  | `tests/integration/test_api.py::test_startup_fails_on_missing_model` (degraded health) and `tests/unit/test_predictor.py::test_predictor_class_count_mismatch_raises`. | PASS |
| F5.AC4  | `tests/integration/test_api.py::test_health_reports_model_loaded` and `tests/unit/test_health.py::test_health_returns_ok`. | PASS |
| F5.AC5  | `tests/integration/test_api.py::test_parallel_predicts_succeed` fires two parallel `/api/predict` calls in threads. | PASS |
| F5.AC6  | `tests/unit/test_validate.py::test_validate_text_renamed_jpg_rejected` (content not extension); `test_validate_oversize_rejected` (5 MB cap). | PASS |

## F6 — Frontend

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F6.AC1  | `tests/e2e/test_frontend.py::test_console_no_errors` and `::test_index_loads_no_external_hosts[chromium]` (Playwright records all network traffic; asserts no off-host calls). | PASS |
| F6.AC2  | `tests/e2e/test_frontend.py::test_language_toggle_persists[chromium]` (toggles EN/Bangla, reloads, checks persistence). | PASS |
| F6.AC3  | `tests/e2e/test_frontend.py::test_upload_predict_and_render[chromium]` injects a 4000-px image and asserts the upload payload is ≤ 1024 px on its longest side. | PASS |
| F6.AC4  | `tests/e2e/test_frontend.py::test_upload_predict_and_render[chromium]` covers the not-sure UI path (a low-confidence request returns the "I'm not confident enough" retake tips). | PASS |
| F6.AC5  | `tests/e2e/test_frontend.py::test_no_horizontal_scroll_at_375[chromium]` (375×667 viewport, asserts `document.documentElement.scrollWidth <= clientWidth`). | PASS |
| F6.AC6  | `tests/e2e/test_frontend.py::test_disclaimer_visible[chromium]`.                                         | PASS |

## F7 — Advice content

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F7.AC1  | `tests/unit/test_advice.py::test_advice_schema_all_classes_present` asserts all 19 classes exist with non-empty en/bn and `reviewed_by_human: false`. | PASS |
| F7.AC2  | `tests/unit/test_advice.py::test_advice_guard_rejects_dose_pattern` and `test_advice_guard_rejects_brand`. | PASS |
| F7.AC3  | The `/api/predict` response surfaces the advice entry keyed by the predicted class; covered by the integration smoke against `examples/leaf_03.jpg` and the `test_predict_ok` assertion that `advice` is in the response. | PASS |

## F8 — Operations

| AC      | Test / Artifact                                                                                          | Result |
| ------- | -------------------------------------------------------------------------------------------------------- | ------ |
| F8.AC1  | `docker build -t leafcheck:dev .` succeeds; image size **1.47 GB** recorded in [`DECISIONS.md` D6](DECISIONS.md). | PASS |
| F8.AC2  | `models/model.pt` (5.9 MB) + `class_names.json` + `metrics.json` + `threshold.json` shipped; total `models/` ≈ 5.9 MB < 25 MB cap. | PASS |
| F8.AC3  | `examples/` contains 6 hand-picked synthetic images + `labels.json`; documented as hand-picked + synthetic in `examples/README.md` and `DECISIONS.md` D8. | PASS |
| F8.AC4  | `scripts/smoke_test.sh` exists and is executable (`-rwxr-xr-x`); passes against the Docker image and against a local dev uvicorn. | PASS |
| F8.AC5  | `.github/workflows/ci.yml` runs lint, unit + integration tests, and the smoke training; recorded in the M1 + M3 commits. | PASS |

## Global acceptance (G1–G6)

| AC | Test / Artifact | Result |
| -- | --------------- | ------ |
| G1 | `tests/integration/test_data_pipeline.py::test_verify_reports_zero_overlap` and the leakage-safe split tests in `test_split.py` and `test_hashing.py` (8-orientation grouping). | PASS |
| G2 | `tests/unit/test_preprocess_shared.py` asserts the same `leafcheck.preprocess` module is imported by training, evaluation, and serving. | PASS |
| G3 | The README reports the shipped model's `best_val_macro_f1` with the explicit caveat that the metric is on synthetic data; the limitations section is linked from the API reference. | PASS |
| G4 | `tests/unit/test_validate.py` covers non-image, oversize, corrupt, huge-pixel-count, empty — all return HTTP 400. | PASS |
| G5 | `tests/integration/test_examples.py::test_examples_round_trip` predicts each of the 6 shipped examples against the real API and asserts the class in `examples/labels.json`. | PASS (6/6) |
| G6 | `.github/workflows/ci.yml` runs lint + full test suite; the README's performance table lists **peak RSS = 252 MB** (G6's peak-inference memory). | PASS |

---

## OUT-OF-SCOPE items confirmed *not* built

Per `SCOPE.md` OUT-OF-SCOPE, none of these are in the repo:

* No user accounts / auth.
* No stored uploaded images (the API processes them in memory and discards).
* No database of any kind.
* No GPU serving path (CPU-only by design).
* No mobile app.
* No object detection / segmentation (single classification only).
* No crops other than tomato / potato / corn / bell pepper.
* No pesticide brand names or doses in `data/advice.json` (F7.AC2 enforces this).
* No retraining from the web UI (training is a CLI, not an endpoint).
* No analytics, telemetry, or third-party tracking. The static page makes no off-host network calls (F6.AC1).

## Known limitations (called out in README)

* The shipped `models/model.pt` is **trained on synthetic data** (gradients + solid colour fields) because the headless build sandbox cannot download PlantVillage. The reported `best_val_macro_f1 = 1.0` is on that synthetic data only. The README is explicit about this. Retrain against a PlantVillage copy before deploying for end users.
* Docker image is 1.47 GB. A multi-stage build with a `slim` Python base and torch-cpu wheels could shave ~300 MB; recorded as a future-work item in `BACKLOG.md` if needed.
* No rate limiting, no auth, no TLS termination. Intended for same-origin deployments behind a reverse proxy (see `DEPLOY.md` §4).

## How to verify the project today

From a clean clone:

```bash
docker build -t leafcheck:dev . && docker run --rm -p 8000:8000 leafcheck:dev &
sleep 12
scripts/smoke_test.sh                # should print "All smoke checks passed."
docker rm -f $(docker ps -aq)        # cleanup
```

Or in dev mode:

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/playwright install chromium
.venv/bin/pytest -q                  # 74 unit/integration, ~35 s
.venv/bin/pytest -q tests/e2e        # 6 e2e, ~7 s
.venv/bin/ruff check .               # clean
```

## File map of the audit

```
README.md             user-facing quick-start, API, perf, architecture
SCOPE.md              the contract (F1–F8 + G1–G6)
DECISIONS.md          in-session decisions (D1–D8)
HARDENING.md          H-phase security + 3x stability report
FRESH_CLONE.md        F-phase fresh-clone verification
DEPLOY.md             D-phase deployment topologies
SPACE_README.md       D-phase Hugging Face Space card
FINAL_REPORT.md       X-phase this file
BACKLOG.md            rejected ideas, one line each
BLOCKERS.md           impossible-in-scope items
PLAN.md               milestone breakdown (M1–M7 + H/F/D/R/X)
PROJECT_SPEC.md       original spec, source of SCOPE.md
CLAUDE.md             per-session rules
LICENSE               MIT
data/DATASET_INFO.md  F1.AC3 (PlantVillage license + citation)
data/advice.json      F7 (all 19 classes, en + bn, no doses/brands)
models/               F8.AC2 (shipped model, 5.9 MB)
examples/             F8.AC3 (6 hand-picked + labels.json)
scripts/smoke_test.sh F8.AC4
Dockerfile            F8.AC1 (CPU-only torch, non-root, HEALTHCHECK)
tests/                AC → test mapping (this file is the index)
```

The build is complete. Every AC in `SCOPE.md` is mapped above to a
green test or a present artifact; every "OUT OF SCOPE" item is
confirmed absent. The project is ready to hand off.
