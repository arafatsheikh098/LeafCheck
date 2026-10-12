"""F5: POST /api/predict."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from leafcheck.advice import advice_for
from leafcheck.api import get_advice, get_predictor
from leafcheck.api.schemas import PredictResponse, TopClass
from leafcheck.predictor import Predictor
from leafcheck.validate import ValidationError, validate_image_bytes

router = APIRouter()


@router.post("/api/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(...),
    predictor: Predictor = Depends(get_predictor),
    advice_db: dict = Depends(get_advice),
) -> PredictResponse:
    """Validate the upload, run inference, and return the prediction."""
    data = await file.read()
    try:
        validated = validate_image_bytes(data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.reason) from exc

    pred = predictor.predict(validated.image)
    adv = advice_for(advice_db, pred.class_name)
    return PredictResponse(
        class_name=pred.class_name,
        confidence=pred.confidence,
        not_sure=pred.not_sure,
        top_k=[TopClass(**t) for t in pred.top_k],
        advice=adv,
    )


def get_router() -> APIRouter:
    return router
