#!/usr/bin/env bash
# Train on a GPU machine (or a free GPU notebook). Produces the production
# model under models/. Requires `data/manifest.csv` (run
# `python -m leafcheck.data prepare --source <local-plantvillage-folder> --out data/`
# first).
set -euo pipefail
cd "$(dirname "$0")/.."

python -m leafcheck.train --config configs/train.yaml