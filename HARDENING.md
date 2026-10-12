# Hardening pass (H)

A whole-repo security + stability review run after M7 landed and before
the fresh-clone / deployment / README / scope-audit phases. This file
records the checks and their outcomes so the record is not lost.

## Security review

| Concern                                              | Result | Evidence                                                                 |
| ---------------------------------------------------- | ------ | ------------------------------------------------------------------------ |
| `eval` / `exec` in src/                              | none   | `grep -rn "eval\|exec" src/` returns no source uses (only `model.eval()`). |
| `subprocess` with `shell=True`                       | none   | no matches.                                                              |
| `pickle.load` / `yaml.load` (unsafe)                 | none   | only `yaml.safe_load` is used; no `pickle.load` anywhere.                |
| `torch.load(..., weights_only=...)`                  | safe   | `predictor.py:70` uses `weights_only=True`.                              |
| Hard-coded secrets / tokens / passwords              | none   | `grep -rn "password\|secret\|token" src/` returns no source uses.        |
| CORS / cross-origin                                  | none   | no `CORSMiddleware`; the app is a same-origin service.                   |
| Upload validation (size, content, type)              | covered| `validate.py` enforces 5 MB, JPEG/PNG/WebP, content-not-extension.       |
| Decompression-bomb handling                          | covered| `validate.py` catches `Image.DecompressionBombError` and returns 400.    |
| Path traversal on uploads                            | n/a    | uploads are read as `bytes`; the path is never written to disk.          |
| File-system reads outside repo                       | bounded| only `models/`, `data/`, `static/`, `examples/` are touched at runtime.  |
| Container user                                       | non-root | `Dockerfile` `USER appuser` after `useradd --system`.                  |

## Stability / flakiness

* `pytest -q --ignore=tests/e2e` → **73 passed, 1 skipped, 0 failed** in 3 consecutive runs (35.7 s / 32.4 s / 32.9 s).
* `pytest -q tests/e2e` → **6 passed** in a single run (~6.5 s with a real spawned uvicorn).
* `ruff check .` → **all checks passed** in 3 consecutive runs.
* Docker build (`docker build -t leafcheck:dev .`) → succeeds; image size **1.47 GB**.
* `scripts/smoke_test.sh` against the live Docker container → 6/6 examples predict, 400 on non-image, /health and /api/classes green.

## What was *not* added

The hardening pass deliberately did not add:

* No new dependencies (would need a SCOPE.md exception for F8.ALLOWED STACK).
* No rate limiting (no user accounts, internal/research use only).
* No auth (no user accounts, same).
* No request body size limit at the HTTP layer beyond the 5 MB upload check (uvicorn default of unlimited is fine for an internal demo).
* No TLS termination (the deployment phase will document that the service is intended to sit behind a reverse proxy).

If any of those are wanted later they belong in BACKLOG.md, not in scope.
