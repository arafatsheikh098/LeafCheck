# LeafCheck Makefile
# Conventions: every target runs in a project-local venv created by `make setup`.
# The Python interpreter is pinned to 3.12 (ALLOWED STACK).

PY ?= python3.12
VENV ?= .venv
ACT := . $(VENV)/bin/activate

.PHONY: setup test lint run train-smoke clean docker-build

setup:
	$(PY) -m venv $(VENV)
	$(ACT) && pip install --upgrade pip
	$(ACT) && pip install -e ".[dev]"
	$(ACT) && python -m playwright install --with-deps chromium

test:
	$(ACT) && pytest

lint:
	$(ACT) && ruff check .
	$(ACT) && ruff format --check .

run:
	$(ACT) && uvicorn leafcheck.app.main:app --host 127.0.0.1 --port 8000

train-smoke:
	$(ACT) && python -m leafcheck.train --config configs/smoke.yaml

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist

docker-build:
	docker build -t leafcheck:dev .