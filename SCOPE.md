# SCOPE.md — the contract (do not edit after this point)

> Locked in prompt P0. CLAUDE.md forbids editing this file in later sessions.
> IN SCOPE, OUT OF SCOPE and ALLOWED STACK are copied word-for-word from PROJECT_SPEC.md.

## IN SCOPE
F1 Data pipeline CLI: python -m leafcheck.data prepare --source <URL or local dir> --out data/. Uses the PlantVillage "color" images for exactly these 19 classes: Tomato (10: bacterial spot, early blight, late blight, leaf mold, septoria leaf spot, spider mites, target spot, yellow leaf curl virus, mosaic virus, healthy), Potato (3: early blight, late blight, healthy), Corn/maize (4: cercospora/gray leaf spot, common rust, northern leaf blight, healthy), Bell pepper (2: bacterial spot, healthy). The download must work without a login; if it cannot be verified, accept a local folder and document the exact manual download step. Validate every image; record SHA-256 and perceptual hashes; write data/DATASET_INFO.md with the dataset's license and citation.
F2 Leakage-safe split: group duplicates and near-duplicates BEFORE splitting, including rotated and flipped copies (compute the perceptual hash for all 8 orientations of each image and group two images if any orientation matches within a configured Hamming distance). Split by GROUP, stratified by class, 70/15/15, fixed seed. Write manifests (path, class, group id, split, sha256) and a verify command that re-checks zero overlap.
F3 Training: config-driven (YAML); torchvision MobileNetV3-Small with ImageNet-pretrained weights; augmentation on the training split only; fixed seeds; class-weighted loss when the imbalance ratio exceeds 3; early stopping on validation macro-F1. Saves model.pt, class_names.json, metrics.json (including hardware and training time) and a config snapshot. A CI smoke training run on a tiny synthetic dataset finishes in under 2 minutes.
F4 Evaluation: on the test split only: accuracy, macro-F1, per-class precision/recall/F1, confusion-matrix PNG, and accuracy by confidence bucket. Choose the "not sure" threshold on the VALIDATION split (smallest confidence at which accepted predictions reach the configured precision target, default 95%) and report test coverage at that threshold. Robustness table: test accuracy under synthetic blur, brightness, contrast, JPEG quality, small rotation and center crop. Auto-generate reports/eval.md.
F5 Inference API (FastAPI): POST /api/predict (multipart image, max 5 MB; accept JPEG/PNG/WebP validated by content, not extension; apply EXIF orientation; convert to RGB; reject corrupt files and decompression bombs with clear 4xx errors). Response: status ("ok" or "not_sure"), top3 [{class_id, crop, condition, confidence}], advice {en, bn}, model_version, disclaimer. Also GET /api/classes, GET /api/model-info, GET /health (reports model loaded). Model loads once at startup; CPU only; torch.inference_mode; single worker; start-up fails loudly if model files are missing or the class count mismatches.
F6 Frontend: one mobile-first page (HTML/CSS/vanilla JS, no CDN): take a photo or choose a file (accept="image/*" capture="environment"), preview, client-side downscale to at most 1024px before upload, EN/Bangla toggle remembered in localStorage, results with confidence bars, a "not sure" state that tells the user how to retake the photo (single leaf, good light, plain background), friendly error states, and a visible disclaimer.
F7 Advice content: data/advice.json for each of the 19 classes: short description, what to do (general and conservative), when to contact a local agricultural extension officer; English and Bangla; field reviewed_by_human: false until the owner changes it. Never recommend pesticide brands or doses.
F8 Operations: Dockerfile with CPU-only PyTorch, non-root user, small image; models/ committed (at most 25 MB) with metrics.json; examples/ with 6 correctly classified test images and their expected labels (documented as hand-picked); scripts/smoke_test.sh; CI.

## OUT OF SCOPE
User accounts, storing uploaded images, any database, GPU serving, a mobile app, object detection or segmentation, other crops, pesticide brands or doses, retraining from the web UI, analytics, anything not listed above.

## ALLOWED STACK
Python 3.11 or 3.12; PyTorch and torchvision (CPU wheels); Pillow; imagehash; numpy; scikit-learn (metrics only); matplotlib (plots only); PyYAML; FastAPI; uvicorn; python-multipart; pydantic; pytest; httpx; pytest-playwright; ruff; Docker; GitHub Actions.

## ACCEPTANCE CRITERIA (one testable check per feature)

### F1 — Data pipeline CLI
- F1.AC1 A test invokes `python -m leafcheck.data prepare` against a local folder of synthetic images and asserts a manifest is written, with at least one row per (class, image) and SHA-256 recorded.
- F1.AC2 A test asserts corrupt images are skipped and counted in the run report without crashing the run.
- F1.AC3 `data/DATASET_INFO.md` is created and contains the dataset license and a citation.
- F1.AC4 The CLI accepts both a URL and a local folder as `--source`.

### F2 — Leakage-safe split
- F2.AC1 A test plants exact duplicates, near-duplicates, rotated copies and flipped copies in a synthetic set; the grouping step puts them in the same group; splitting by group places each planted group entirely in one split.
- F2.AC2 A test asserts the per-class split proportions are within 1% of 70/15/15 where class size allows.
- F2.AC3 A `verify` CLI command (and a test) re-loads the manifests and asserts zero SHA-256 overlap and zero perceptual-hash-group overlap across train/val/test.
- F2.AC4 Manifests are written as CSV with columns: path, class, group_id, split, sha256.

### F3 — Training
- F3.AC1 A test runs training twice on the synthetic smoke set with the same seed and asserts macro-F1 is identical within a stated tolerance.
- F3.AC2 Saved artifacts (`model.pt`, `class_names.json`, `metrics.json`, config snapshot) load and produce a prediction in a test.
- F3.AC3 A test asserts predictions for an image are identical (within tolerance) whether it is batched alone or with others (BatchNorm-eval-mode guarantee).
- F3.AC4 CI smoke training on a tiny synthetic dataset finishes in under 2 minutes.
- F3.AC5 The class-weighted loss is used when the imbalance ratio exceeds 3 (test asserts the flag is set on a synthetic imbalanced set).

### F4 — Evaluation and threshold
- F4.AC1 A test asserts the "not sure" threshold selection reads only the validation split, never the test split.
- F4.AC2 A single command reproduces all test-split metrics (accuracy, macro-F1, per-class P/R/F1, confusion-matrix PNG, accuracy by confidence bucket).
- F4.AC3 `reports/eval.md` is auto-generated, includes the chosen threshold, the coverage at that threshold, and a plain-language limitations section.
- F4.AC4 A robustness table is produced with columns: blur, brightness, contrast, JPEG quality, small rotation, center crop, with accuracy for each.
- F4.AC5 `threshold.json` is saved next to the model and is read by the API.

### F5 — Inference API
- F5.AC1 Tests cover all of: EXIF-rotated JPEG, RGBA PNG, grayscale image, truncated JPEG, 6 MB file (rejected), a PNG with an extreme pixel count (rejected safely), a text file renamed .jpg (rejected), and an empty upload (rejected).
- F5.AC2 The "not_sure" logic is unit-tested with mocked logits at, below, and above the threshold.
- F5.AC3 The API start-up fails with a clear error if model files are missing or the class count mismatches.
- F5.AC4 `GET /health` reports `model_loaded: true|false`.
- F5.AC5 A test fires two parallel `/api/predict` requests and both succeed.
- F5.AC6 Image content is validated, not the file extension; max 5 MB upload is enforced.

### F6 — Frontend
- F6.AC1 The page uses vanilla HTML/CSS/JS with no external CDN requests (Playwright test asserts no off-host network calls).
- F6.AC2 EN/Bangla toggle is remembered in localStorage (test asserts the toggle persists across reloads).
- F6.AC3 Client-side downscale to at most 1024px before upload (test asserts a 4000-px image is downscaled before the request is sent).
- F6.AC4 A "not sure" state shows retake instructions (single leaf, good light, plain background) and friendly error states exist for bad uploads.
- F6.AC5 The page has no horizontal scroll at a 375px viewport (Playwright test).
- F6.AC6 A visible disclaimer is rendered.

### F7 — Advice content
- F7.AC1 A schema test asserts all 19 classes are present, with non-empty English and Bangla strings, and a `reviewed_by_human` field.
- F7.AC2 A guard test fails if any advice text contains a dose pattern (e.g. `\d+\s*(ml|mg|g/L|kg/ha)`) or a brand word from a configurable list.
- F7.AC3 The advice object surfaced by `/api/predict` matches the schema in `data/advice.json` for the predicted class.

### F8 — Operations
- F8.AC1 `docker build` succeeds and the image size is recorded in `DECISIONS.md`.
- F8.AC2 `models/` contains the shipped weights, `class_names.json`, `metrics.json` (and `threshold.json` from F4); total `models/` size is at most 25 MB.
- F8.AC3 `examples/` contains 6 hand-picked images with a `labels.json` mapping filename → expected class, documented as hand-picked.
- F8.AC4 `scripts/smoke_test.sh` exists and is executable.
- F8.AC5 CI workflow runs lint, tests, and the synthetic smoke training.

### Global acceptance (from PROJECT_SPEC.md)
- G1 Zero overlap between train/val/test by SHA-256 and by perceptual-hash group, including rotated and flipped variants (test + verify command).
- G2 One shared preprocessing module is used by training, evaluation and serving (test asserts they call the same function).
- G3 README reports test macro-F1 honestly with the limitation text.
- G4 API rejects non-images, files over 5 MB, corrupt files, over-large pixel counts, empty uploads.
- G5 Each `examples/` file returns its expected class via the real API in a test.
- G6 CI is green including synthetic smoke training; peak inference memory is measured and recorded in the README.
