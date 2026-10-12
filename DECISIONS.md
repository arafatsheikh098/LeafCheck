# DECISIONS.md — log of in-session decisions

> Per CLAUDE.md: when something is ambiguous, the agent picks the simplest option that fits SCOPE.md and records it here. No questions back to the user.

## M1 (Foundation)
- D1: Pin `python_requires>=3.11,<3.13` so we use the system Python 3.12 at `/opt/homebrew/bin/python3.12`. System default is 3.14 which is outside ALLOWED STACK; the Makefile uses `python3.12` explicitly so venv and CI are reproducible regardless of which `python3` is on PATH.
- D2: M1 Docker image (`leafcheck:dev`) is **1.07 GB** uncompressed. The plan only requires recording the size in DECISIONS.md, but it is large because `python:3.12-slim` plus CPU-only torch + torchvision weigh ~1 GB. We will revisit (slimmer base, multi-stage build) in M7 if the final deployment target needs it. Recorded on 2026-10-12 via `docker images leafcheck:dev`.

