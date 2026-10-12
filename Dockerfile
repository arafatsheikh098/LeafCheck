# syntax=docker/dockerfile:1.7
# CPU-only PyTorch image. Builds on a clean clone with just pyproject.toml
# and src/. The model + advice + frontend + examples are baked in at
# build time so the image is a self-contained deployable.
FROM python:3.12-slim AS base

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# CPU-only torch wheels come from the official PyTorch index. We pin the
# versions in pyproject.toml so the dry-run check matches.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system appuser \
 && useradd --system --gid appuser --create-home --shell /bin/bash appuser

WORKDIR /app

# Install Python deps. Torch is heavy, so it's cached as its own layer
# against pyproject.toml only. The `src/` tree must be present before
# `pip install -e .` because setuptools' egg_info scans for packages.
# We pass `--no-deps` to torch so it doesn't pull CUDA wheels from PyPI
# and override our CPU-only index; the second install pulls the rest of
# the dependency tree (FastAPI, uvicorn, …) from PyPI.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-deps --index-url "${TORCH_INDEX_URL}" \
    "torch==2.4.1" "torchvision==0.19.1"
RUN pip install -e .

# Application code, model artifacts, advice, examples, static frontend.
COPY models ./models
COPY data ./data
COPY static ./static
COPY examples ./examples
COPY scripts ./scripts

USER appuser

EXPOSE 8000

# Liveness probe: hit /health on the local port. curl is installed above.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "leafcheck.app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]