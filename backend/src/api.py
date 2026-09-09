"""FastAPI wrapper over the two-stage triage graph.

Exposes a deterministic flagged-PO list and a live triage endpoint. The heavy
graph/model stack is imported lazily (only on startup or per triage call) so the
app and its lighter routes stay importable and testable without loading Harrier.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api_schemas import FlaggedPosResponse
from .flagged import build_flagged_pos


def _frontend_origins() -> list[str]:
    """Return the allowed CORS origins from env, defaulting to the Next dev host."""
    raw = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(graph: Optional[Any] = None, prewarm_startup: bool = True) -> FastAPI:
    """Build the FastAPI app.

    :param graph: Optional pre-built/compiled graph (or fake) for tests; when set,
        startup prewarm is skipped and this graph is used for /triage.
    :param prewarm_startup: When True and no graph is injected, prewarm the model
        and build the real graph on startup.
    :returns: The configured FastAPI application.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.graph is None and prewarm_startup:
            # Imported here so importing this module stays light for tests.
            from .graph import build_triage_graph
            from .retrieval import prewarm

            prewarm()
            app.state.graph = build_triage_graph()
        yield

    app = FastAPI(title="PO Exception Triage API", lifespan=lifespan)
    app.state.graph = graph

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_frontend_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    @app.get("/flagged-pos", response_model=FlaggedPosResponse)
    def flagged_pos() -> FlaggedPosResponse:
        """Return the deterministically tiered flagged-PO list (no LLM)."""
        items = build_flagged_pos()
        return FlaggedPosResponse(count=len(items), items=items)

    return app


app = create_app()
