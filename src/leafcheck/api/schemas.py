"""F5: Pydantic response schemas for the inference API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TopClass(BaseModel):
    class_name: str = Field(alias="class")
    confidence: float


class PredictResponse(BaseModel):
    class_name: str
    confidence: float
    not_sure: bool
    top_k: list[TopClass]
    advice: dict[str, Any] | None = None


class ClassesResponse(BaseModel):
    classes: list[str]


class ModelInfoResponse(BaseModel):
    model_loaded: bool
    num_classes: int
    image_size: int
    threshold: dict[str, Any] | None
    metrics: dict[str, Any] | None


class HealthResponse(BaseModel):
    status: str
    service: str
    model_loaded: bool
