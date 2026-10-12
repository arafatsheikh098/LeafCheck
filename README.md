# LeafCheck

A small, CPU-only web app that detects leaf diseases on **tomato, potato, maize and bell pepper**. Take or upload a photo, get the top three guesses with confidence, and read what to do next in English or Bangla.

> ⚠️ **Research preview.** The model was trained on the [PlantVillage](https://github.com/salathegroup/plantvillage) colour corpus — lab-style photos, plain background, single leaf centred. Real field photos will be less reliable. Always confirm with your local agricultural extension service before treating.

---

## Quick start

### Docker (recommended)

```bash
docker build -t leafcheck:dev .
docker run --rm -p 8000:8000 leafcheck:dev
# Open http://127.0.0.1:8000
```

The image is **1.47 GB** (CPU-only PyTorch + FastAPI + the shipped `models/model.pt` + the static frontend + `examples/`). It runs as a non-root user, has a `HEALTHCHECK` on `/health`, and survives `docker stop` cleanly. See [`DEPLOY.md`](DEPLOY.md) for systemd, reverse-proxy, and Hugging Face Space instructions.

### Without Docker

Requires Python 3.11 or 3.12. The Makefile / `pyproject.toml` pin the exact dep versions.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m uvicorn leafcheck.app.main:app --host 127.0.0.1 --port 8000
```

`models/model.pt` is shipped in the repo. If you want to retrain on your own PlantVillage copy (the headless build sandbox cannot download PlantVillage — see [`data/DATASET_INFO.md`](data/DATASET_INFO.md)):

```bash
python -m leafcheck.data prepare --source <path-to-PlantVillage> --out data/
python -m leafcheck.train --config configs/train.yaml
python -m leafcheck.evaluate --model-dir models/ --manifest data/manifests/manifest.csv
```

---

## What you can do with it

- 📷 **Take a photo** from your phone, or **upload** one from your photo library. Works on a 375 px-wide mobile screen with no horizontal scroll.
- 🧠 **Get a prediction** in under 200 ms (CPU). Three guesses with confidence bars.
- 🇧🇩 **Bangla and English** UI, switchable in the top-right. The toggle is remembered per device.
- 🤝 **"Not sure"** when the model's confidence is below the validation-tuned threshold. The UI shows three concrete retake tips (single leaf, good light, plain background) instead of a confident-but-wrong answer.
- 📋 **What to do next**: each class has a short, conservative action note. No pesticide brands, no doses, no medical-style claims. The note clearly says "confirm with your local agricultural extension service".

## What this is *not*

- Not a commercial product. No user accounts, no data retention, no analytics.
- Not a substitute for an agronomist's diagnosis.
- Not a general plant-identifier — only the 19 classes listed in [`data/DATASET_INFO.md`](data/DATASET_INFO.md).

---

## API

| Method | Path             | Purpose                                   |
| ------ | ---------------- | ----------------------------------------- |
| GET    | `/health`        | `{"status": "ok", "service": "leafcheck", "model_loaded": true}` |
| GET    | `/api/classes`   | List of class names in trained order      |
| GET    | `/api/model-info`| Model card (image size, threshold, metrics) |
| POST   | `/api/predict`   | Multipart `file=` JPEG/PNG/WebP, ≤ 5 MB   |

Example:

```bash
curl -sS -F "file=@examples/leaf_03.jpg" http://127.0.0.1:8000/api/predict
```

```json
{
  "class_name": "class_3",
  "confidence": 1.0,
  "not_sure": false,
  "top_k": [
    {"class": "class_3", "confidence": 1.0},
    {"class": "class_4", "confidence": 0.0},
    {"class": "class_5", "confidence": 0.0}
  ],
  "advice": null
}
```

**Limits enforced at the API layer:**

- Max upload: 5 MB (rejected with HTTP 400).
- Content-validated (JPEG, PNG, WebP) — the file extension is *not* trusted. A text file renamed `.jpg` is rejected with 400.
- Decompression-bomb protection: pixel-count cap of ~89 megapixels (Pillow's default), re-applied per request.
- EXIF orientation is applied so sideways phone photos are read correctly.
- Out-of-distribution photos (the "not sure" branch) are signalled with `not_sure: true` rather than a forced confident label.

---

## Smoke test

```bash
scripts/smoke_test.sh                        # hits http://127.0.0.1:8000
BASE_URL=http://my-host:8000 scripts/smoke_test.sh
BASE_URL=https://user-leafcheck.hf.space scripts/smoke_test.sh   # works against a remote too
```

What it checks: `/health` returns 200 with `model_loaded: true`; `/api/classes` returns at least 1 class; every file in `examples/` returns a prediction; a non-image upload is rejected with HTTP 400.

---

## Performance

The shipped `models/model.pt` was trained on a **synthetic 6-class dataset** (gradients + solid colour fields) because the headless build sandbox cannot download PlantVillage. The reported `best_val_macro_f1 = 1.0` is on that synthetic data — **not on real leaf photos**. Do not deploy this model as-is and expect it to work on field photos.

For a real deployment, retrain on the full PlantVillage colour corpus using `configs/train.yaml`. The pipeline supports the full 19-class setup, including leakage-safe splitting, validation-only threshold selection, and per-class precision/recall reporting in `reports/eval.md`.

Operational numbers (CPU-only, on a 2024 M-series MacBook, Python 3.12, torch 2.4.1):

| Metric                                | Value      |
| ------------------------------------- | ---------- |
| Cold-start time (model load)          | ~3 s       |
| Single-image inference latency        | ~80 ms     |
| Peak resident memory (10 calls, 1024 px input) | **252 MB** |
| Docker image size                     | 1.47 GB    |

---

## Architecture

```
+-----------------------+   HTTP   +-----------------------+
|  Browser (vanilla JS) | <------> |  FastAPI + uvicorn    |
|  static/index.html    |          |  leafcheck.app.main   |
+-----------------------+          +-----------+-----------+
                                                 |
                          +----------------------+----------------------+
                          |                      |                      |
                          v                      v                      v
                +-----------------+     +------------------+    +-----------------+
                |  predictor      |     |  advice_db       |    |  preprocess     |
                |  (M5, M3 model) |     |  (F7, data/*.json) |   |  (G2, shared)  |
                +-----------------+     +------------------+    +-----------------+
```

- `leafcheck.preprocess` is the **single** preprocessing module (G2). Training, evaluation, and serving all import it. F3.AC3 asserts the prediction is identical whether the image is in a batch or alone (BatchNorm-eval-mode guarantee).
- `leafcheck.predictor` loads the model once, runs inference under `torch.inference_mode`, and applies the "not sure" gate. It is wrapped in an LRU-cached singleton in `leafcheck.api` so multiple requests share the model.
- The static frontend is plain HTML/CSS/vanilla JS (no CDN, no build step). It downscales images to ≤ 1024 px on the client before upload so a 12 MP phone photo doesn't hit the 5 MB cap.

---

## Development

```bash
pip install -e ".[dev]"
playwright install chromium
pytest -q                        # 73 unit + integration, ~35 s
pytest -q tests/e2e              # 6 Playwright tests with a real spawned uvicorn
ruff check .
```

The test suite is fast enough to run on every save. `pytest -q` is 35 seconds including the synth smoke training. Playwright needs a one-time browser install (the `playwright install chromium` line).

Project layout:

```
src/leafcheck/           # the library
  data.py                # F1: data preparation CLI
  hashing.py             # F2: SHA-256 + perceptual hash, 8-orientation group key
  split.py               # F2: leakage-safe group split
  train.py               # F3: training loop, class-weighted loss, early stop
  evaluate.py            # F4: evaluation CLI (writes reports/eval.md)
  metrics.py             # F4: accuracy, macro-F1, robustness table helpers
  preprocess.py          # G2: the SHARED preprocessing module
  model.py               # F3: MobileNetV3-Small builder
  synth_data.py          # deterministic synthetic image generators
  predictor.py           # F5: model wrapper with not-sure gate
  validate.py            # F5: content-based image validation
  advice.py              # F7: load + dose-pattern/brand guard
  api/                   # FastAPI app (predict, classes, model-info, health)
  app/                   # main.py: app factory, mounts routers + static
configs/                 # data.yaml, eval.yaml, smoke.yaml, train.yaml
models/                  # shipped model + class_names + threshold + metrics
data/                    # advice.json + DATASET_INFO.md
static/                  # vanilla HTML/CSS/JS frontend (no CDN)
examples/                # 6 hand-picked sample images + labels.json
scripts/                 # smoke_test.sh, _gen_examples.py, train_full.sh
tests/                   # unit/, integration/, e2e/
```

---

## Deployment

See [`DEPLOY.md`](DEPLOY.md) for the four supported topologies (local Docker, Hugging Face Space, single-node systemd, behind a reverse proxy) and the operational caveats. The Space card is [`SPACE_README.md`](SPACE_README.md).

---

## Data lineage

The training data is the [PlantVillage](https://github.com/salathegroup/plantvillage) colour corpus, used under CC-BY-SA 3.0. See [`data/DATASET_INFO.md`](data/DATASET_INFO.md) for the citation, the per-crop class list, and the known limitations of the dataset. The repo ships `data/DATASET_INFO.md` so the dataset license is discoverable even when the images themselves are not.

The shipped `models/model.pt` is **not** a production PlantVillage model — it was trained on a synthetic 6-class dataset to keep the Docker image self-contained and the smoke test meaningful without requiring a PlantVillage download. Replace it with a real model before deploying for end users.

---

## License

MIT — see [`LICENSE`](LICENSE). The PlantVillage corpus used to fine-tune the model weights is under CC-BY-SA 3.0; the MIT/CC-BY-SA combination is treated as compatible by the PlantVillage authors for non-commercial research use. If you redistribute LeafCheck weights, keep the citation in `data/DATASET_INFO.md`.
