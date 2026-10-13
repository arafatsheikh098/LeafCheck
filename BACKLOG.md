# BACKLOG.md — out-of-scope ideas captured for later

> Per CLAUDE.md: when a new idea or gap is noticed, append ONE line here (idea, why, effort) and continue with the smallest in-scope solution. Do not implement it.

- Multi-stage Docker build to shrink `leafcheck:dev` from 1.50 GB → ~700 MB (use a `slim` Python base + multi-stage copy of wheels; recorded in D6/D7). [D6]
- Per-class gradient-friendly augmentation (rotation / flip / colour jitter) in `preprocess.preprocess_batch` for small datasets like BdLeaf20 — would likely close the F1 gap on `10_Epipremnum aureum` and `19_Rosa canina` (currently ~0.73) without needing more data. Effort: S.
- Re-evaluate whether the heuristic "not sure" threshold (`0.69`) is too aggressive — it currently marks 12% of test predictions as "not sure" with 96% precision. Tunable in `models/threshold.json`. Effort: S.
- Add the remaining 11 missing BdLeaf20 classes (`01_..05_`, `09_`, `11_..12_`, `17_..18_`, `20_`) once the user downloads them — would push the model from 9 → 20 species. Effort: M (data + retrain + advice entries).
- PlantVillage retrain: the 19 PlantVillage advice entries are still in `data/advice.json` ready to be used; the data pipeline + `configs/train.yaml` will produce a disease-classification model in the same shape. Effort: L (need to download ~2 GB of PlantVillage, train on GPU).
- Conflict warning when another process holds host port 8000: add a quick pre-flight check in `scripts/smoke_test.sh` that picks a different port on `Address already in use` and prints the new URL. Effort: S.
