# Fresh-clone test (F)

Run the day after M7 to make sure a brand-new clone of the repo can go
from `git clone` to "the smoke test is green" without any of the
in-tree dev conveniences (the existing `.venv`, cached wheels, prior
training runs, etc.).

## What was tested

* `git clone <repo> /tmp/fresh-clone-test`
* `cd /tmp/fresh-clone-test && git log --oneline -1` → `merge: H hardening pass` (latest commit on `main`)
* `ls models/ examples/ data/` → `model.pt` (5.9 MB) + `class_names.json` + `metrics.json` + `threshold.json`; `examples/leaf_0?.jpg` + `labels.json` + `README.md`; `advice.json` + `DATASET_INFO.md`. All shipped artefacts present.
* **Docker path**: `docker build -t leafcheck:fresh-clone-test .` → succeeds; image is `Up 12 seconds (healthy)`; `BASE_URL=http://127.0.0.1:8001 scripts/smoke_test.sh` → **6/6 examples predict correctly, 400 on non-image, all green**.
* **Dev path**: `python3.12 -m venv .venv && .venv/bin/pip install -e .` → installs all 43 deps; `uvicorn leafcheck.app.main:app` → serves; same smoke test → **6/6 correct, 400 on non-image, all green**.

## Outcome

PASS — both the documented Docker quick-start and the documented
non-Docker quick-start (from `README.md`) reproduce the full
end-to-end flow with no manual intervention beyond `pip install -e .`
and `docker build`.

## What was *not* tested here

* The full pytest suite (73 unit/integration + 6 e2e) was not run in
  the fresh clone because the dev extras (`pip install -e .[dev]`) are
  a documented separate step in the README. The CI workflow runs them
  on every push.
* Browser-based interaction with the served page was exercised in the
  M6 e2e test (Playwright), which uses the same dev-uvicorn subprocess
  fixture and is green.
