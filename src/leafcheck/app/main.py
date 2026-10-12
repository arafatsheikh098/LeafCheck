"""FastAPI app factory and health endpoint (M1).

The full /api/predict surface lands in M5. This module must stay importable and
have a working /health even before model files exist, so that the M1 milestone
gate is testable on a fresh checkout.
"""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="LeafCheck",
        version="0.1.0",
        description="Leaf disease detector for tomato, potato, maize and bell pepper.",
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        """Liveness probe.

        In M5 this will additionally report whether the model is loaded. In M1
        we only need to confirm the service is up.
        """
        return {
            "status": "ok",
            "service": "leafcheck",
            "model_loaded": False,
        }

    return app


# `uvicorn leafcheck.app.main:app` should just work for local dev.
app = create_app()
