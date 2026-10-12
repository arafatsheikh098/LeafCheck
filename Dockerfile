# syntax=docker/dockerfile:1.7
# CPU-only PyTorch image. The non-root user is created in M7 (it needs the
# static files served too); for now `appuser` is created as a no-op for M1.
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
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system appuser \
 && useradd --system --gid appuser --create-home --shell /bin/bash appuser

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --index-url "${TORCH_INDEX_URL}" "torch==2.4.1" "torchvision==0.19.1"
RUN pip install --no-deps -e .

USER appuser

EXPOSE 8000

# Final entrypoint/HEALTHCHECK arrive in M7.
CMD ["python", "-c", "import leafcheck; print(leafcheck.__version__)"]