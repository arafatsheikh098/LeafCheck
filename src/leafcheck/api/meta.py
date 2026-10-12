"""F5: GET /api/classes, /api/model-info, /health."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends

from leafcheck.api import get_predictor
from leafcheck.api.schemas import ClassesResponse, HealthResponse, ModelInfoResponse
from leafcheck.predictor import Predictor

router = APIRouter()


@lru_cache(maxsize=1)
def _load_metrics(model_dir_str: str) -> dict | None:
    p = Path(model_dir_str) / "metrics.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


@router.get("/api/classes", response_model=ClassesResponse)
def classes(predictor: Predictor = Depends(get_predictor)) -> ClassesResponse:
    return ClassesResponse(classes=predictor.class_names)


@router.get("/api/model-info", response_model=ModelInfoResponse)
def model_info(predictor: Predictor = Depends(get_predictor)) -> ModelInfoResponse:
    metrics = _load_metrics(str(predictor.model_dir.resolve()))
    threshold = None
    if predictor.threshold is not None:
        threshold = {
            "threshold": predictor.threshold.threshold,
            "target_precision": predictor.threshold.target_precision,
            "val_precision_at_threshold": predictor.threshold.val_precision_at_threshold,
            "val_coverage_at_threshold": predictor.threshold.val_coverage_at_threshold,
        }
    return ModelInfoResponse(
        model_loaded=True,
        num_classes=len(predictor.class_names),
        image_size=predictor.image_size,
        threshold=threshold,
        metrics=metrics,
    )


@router.get("/health", response_model=HealthResponse)
def health(predictor: Predictor = Depends(get_predictor)) -> HealthResponse:
    # If we got here without raising, the predictor dependency loaded
    # successfully and the model file is good.
    return HealthResponse(
        status="ok",
        service="leafcheck",
        model_loaded=True,
    )


def get_router() -> APIRouter:
    return router
