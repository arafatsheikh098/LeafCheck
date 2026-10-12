# LeafCheck

A small, CPU-only web app that detects leaf diseases on **tomato, potato, maize and bell pepper**. Take or upload a photo, get the top three guesses with confidence, and read what to do next in English or Bangla.

LeafCheck is a research preview. It is trained on the [PlantVillage](https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset) colour corpus (lab-style photos, plain background, single leaf centred). Field photos will be less reliable. Always confirm with your local agricultural extension service before treating.

## Quick start (Docker)

```bash
docker build -t leafcheck:dev .
docker run --rm -p 8000:8000 leafcheck:dev
# Open http://127.0.0.1:8000
```

Or, without Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m leafcheck.cli train --config configs/smoke.yaml --out models/
python -m uvicorn leafcheck.app.main:app --host 127.0.0.1 --port 8000
```

## API

| Method | Path             | Purpose                                   |
| ------ | ---------------- | ----------------------------------------- |
| GET    | `/health`        | Liveness + whether the model is loaded    |
| GET    | `/api/classes`   | Class index in trained order              |
| GET    | `/api/model-info`| Model card (version, threshold, classes)  |
| POST   | `/api/predict`   | Multipart `file=` JPEG/PNG/WebP, ≤5 MB    |

Example:

```bash
curl -sS -F "file=@examples/leaf_03.jpg" http://127.0.0.1:8000/api/predict
```

The response carries `class_name`, `confidence`, `not_sure`, `top_k`, and `advice {en, bn}`. When confidence is below the chosen "not sure" threshold (selected on the validation split to reach 95% precision), `not_sure` is `true` and the UI shows retake tips instead of a confident diagnosis.

## Smoke test

```bash
scripts/smoke_test.sh                       # hits http://127.0.0.1:8000
BASE_URL=http://my-host:8000 scripts/smoke_test.sh
```

The script hits `/health`, `/api/classes`, runs a real prediction on every file in `examples/`, and confirms a non-image upload is rejected with 400.

## Development

```bash
pip install -e ".[dev]"
playwright install chromium
pytest -q
ruff check .
```

## License

MIT — see [LICENSE](LICENSE). Model weights are derived from torchvision's ImageNet-pretrained MobileNetV3-Small and fine-tuned on PlantVillage. PlantVillage is cited in [data/DATASET_INFO.md](data/DATASET_INFO.md).
