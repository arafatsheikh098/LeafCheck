---
title: LeafCheck
emoji: 🌿
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Identify 9 plant species from a single leaf photo (BdLeaf20).
---

# LeafCheck

A small, CPU-only web app that identifies **9 plant species from a single leaf photo**. Take or upload a photo, get the top three guesses with confidence, and read a short care note (light, water, soil, common pests) in English or Bangla.

This is a Hugging Face Space running the same Docker image described in [`README.md`](../README.md) at the project root. It is a research preview — the model was trained on the [BdLeaf20](https://www.kaggle.com/datasets) leaf-image dataset (9 tropical plant species, ~40–55 images per class, single-leaf close-ups on plain backgrounds). Real field photos will be less reliable than the test-split numbers suggest. Always confirm with a botanist or local extension service before relying on the result for any decision.

## What it identifies

The shipped model recognises 9 species: pomelo (*Citrus grandis*), ivy gourd (*Coccinia grandis*), garden croton (*Codiaeum variegatum*), golden pothos (*Epipremnum aureum*), Chinese hibiscus (*Hibiscus rosa-sinensis*), hyacinth bean (*Lablab purpureus*), mast tree (*Monoon longifolium*), date palm (*Phoenix dactylifera*), dog rose (*Rosa canina*). It is a **species** identifier, not a disease detector — leaves of any of these species with disease symptoms will still be classified as their species.

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

The response carries `class_name`, `confidence`, `not_sure`, `top_k`, and `advice {en, bn}`. When confidence is below the chosen "not sure" threshold (selected on the validation split to reach 95% precision), `not_sure` is `true` and the UI shows retake tips instead of a confident species label.

## Frontend

Open the Space URL in a phone browser. The page is in plain HTML + vanilla JS (no CDN), with a Bangla toggle in the top right that remembers the choice in `localStorage`. Photo capture works directly from the browser's camera on mobile (`<input type="file" accept="image/*" capture="environment">`).

## Limitations

* Trained on BdLeaf20 — only 9 species (out of ~20 in the source dataset, of which only 9 were present in the local copy). Other plants, diseased leaves, field photos with multiple plants in frame, or photos that aren't leaves at all are out of distribution and the model will likely return `not_sure: true` or a low-confidence guess.
* ~40–55 images per class is a small training set; per-class F1 ranges from 0.73 (lowest) to 1.00 (highest) on the test split. See `reports/eval.md` in the project repo for the full confusion matrix.
* 5 MB upload cap. Larger uploads are rejected with HTTP 400.
* No data retention: uploaded images are not stored anywhere.

## Source

The full source (training pipeline, tests, Dockerfile, CI, advice content) is in the project repo. See `DEPLOY.md` for the deployment topologies this image supports.
