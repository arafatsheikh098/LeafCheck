"""F5: Pydantic response schemas for the inference API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# `model_loaded` collides with Pydantic v2's protected `model_*` namespace;
# opt out so the warning goes away (and so the field name stays in the JSON
# response contract that F5 defines).
class _NoModelNS(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class TopClass(_NoModelNS):
    class_name: str = Field(alias="class")
    confidence: float


class PredictResponse(_NoModelNS):
    class_name: str
    confidence: float
    not_sure: bool
    top_k: list[TopClass]
    advice: dict[str, Any] | None = None


class ClassesResponse(_NoModelNS):
    classes: list[str]


class ModelInfoResponse(_NoModelNS):
    model_loaded: bool
    num_classes: int
    image_size: int
    threshold: dict[str, Any] | None
    metrics: dict[str, Any] | None


class HealthResponse(_NoModelNS):
    status: str
    service: str
    model_loaded: bool
