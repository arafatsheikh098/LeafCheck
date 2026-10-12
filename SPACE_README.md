---
title: LeafCheck
emoji: 🌿
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Detect leaf diseases on tomato, potato, maize and bell pepper.
---

# LeafCheck

A small, CPU-only web app that detects leaf diseases on **tomato, potato, maize and bell pepper**. Take or upload a photo, get the top three guesses with confidence, and read what to do next in English or Bangla.

This is a Hugging Face Space running the same Docker image described in [`README.md`](../README.md) at the project root. It is a research preview — the model was trained on the [PlantVillage](https://github.com/salathegroup/plantvillage) colour corpus (lab-style photos). Real field photos will be less reliable. Always confirm with your local agricultural extension service before treating.

## API

| Method | Path             | Purpose                                   |
| ------ | ---------------- | ----------------------------------------- |
| GET    | `/health`        | Liveness + whether the model is loaded    |
| GET    | `/api/classes`   | Class index in trained order              |
| GET    | `/api/model-info`| Model card (version, threshold, classes)  |
| POST   | `/api/predict`   | Multipart `file=` JPEG/PNG/WebP, ≤5 MB    |

Example:

```bash
curl -sS -F "file=@leaf.jpg" https://<user>-leafcheck.hf.space/api/predict
```

The response carries `class_name`, `confidence`, `not_sure`, `top_k`, and `advice {en, bn}`. When confidence is below the chosen "not sure" threshold (selected on the validation split to reach 95% precision), `not_sure` is `true` and the UI shows retake tips instead of a confident diagnosis.

## Frontend

Open the Space URL in a phone browser. The page is in plain HTML + vanilla JS (no CDN), with a Bangla toggle in the top right that remembers the choice in `localStorage`. Photo capture works directly from the browser's camera on mobile (`<input type="file" accept="image/*" capture="environment">`).

## Limitations

* Trained on PlantVillage's "color" split — only 19 classes across 4 crops, all on plain backgrounds. Anything else (other crops, field photos, multiple diseases on one leaf) is out of distribution.
* The deployed model in this Space is the small smoke model from `models/model.pt` — it has not been trained on the full 19-class PlantVillage corpus because the headless build sandbox cannot download the dataset (see `data/DATASET_INFO.md`). Retrain against your own PlantVillage copy and replace `models/model.pt` to ship a production model.
* 5 MB upload cap. Larger uploads are rejected with HTTP 400.
* No data retention: uploaded images are not stored anywhere.

## Source

The full source (training pipeline, tests, Dockerfile, CI, advice content) is in the project repo. See `DEPLOY.md` for the deployment topologies this image supports.
