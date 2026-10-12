"""FastAPI app factory (M1 + M5).

M1: app must be importable and have a working /health even before the
model exists. M5: extend the factory to also include /api/predict,
/api/classes, /api/model-info, and the real /health that requires the
model to be loaded (so the API fails fast on misconfiguration).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from leafcheck.api.meta import get_router as meta_router
from leafcheck.api.predict import get_router as predict_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="LeafCheck",
        version="0.1.0",
        description="Leaf disease detector for tomato, potato, maize and bell pepper.",
    )

    # M5: try to load the predictor at startup. If the model file is
    # missing or corrupt, surface a 503 from every /api/* endpoint
    # instead of crashing the process.
    try:
        from leafcheck.api import get_predictor

        get_predictor()  # uses LEAFCHECK_MODEL_DIR / defaults
    except Exception as exc:  # noqa: BLE001
        logger.warning("Predictor failed to load at startup: %s", exc)
        app.state.predictor_error = str(exc)
    else:
        app.state.predictor_error = None

    @app.exception_handler(RuntimeError)
    async def _runtime_error_handler(_: Request, exc: RuntimeError) -> JSONResponse:
        # 503 if the predictor failed at startup, else re-raise.
        return JSONResponse(
            status_code=503,
            content={"detail": f"model unavailable: {exc}"},
        )

    @app.get("/health", include_in_schema=False)
    def health() -> dict:
        if app.state.predictor_error:
            return {"status": "degraded", "service": "leafcheck", "model_loaded": False}
        return {"status": "ok", "service": "leafcheck", "model_loaded": True}

    # Mount the API routers.
    app.include_router(meta_router())
    app.include_router(predict_router())

    # Mount the static frontend (added in M6). The path may not exist
    # yet, so we mount only if it does.
    static_dir = Path(__file__).resolve().parents[3] / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


# `uvicorn leafcheck.app.main:app` should just work for local dev.
app = create_app()
