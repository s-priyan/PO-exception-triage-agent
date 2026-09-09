"""FastAPI wrapper over the two-stage triage graph.

Exposes a deterministic flagged-PO list and a live triage endpoint. The heavy
graph/model stack is imported lazily (only on startup or per triage call) so the
app and its lighter routes stay importable and testable without loading Harrier.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api_schemas import FlaggedPosResponse, TriageRequest, TriageResponse
from .flagged import build_flagged_pos
from .service import run_triage

_BACKEND_DIR = Path(__file__).resolve().parents[1]


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
            from dotenv import load_dotenv

            from .graph import build_triage_graph
            from .retrieval import prewarm

            # Load OPENAI_API_KEY etc. from backend/.env before building the graph,
            # which constructs ChatOpenAI and needs the key at startup (the CLI
            # entrypoint loads it the same way).
            load_dotenv(_BACKEND_DIR / ".env")
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

    @app.post("/triage", response_model=TriageResponse)
    def triage(request: TriageRequest) -> TriageResponse:
        """Run the live agent for one planner question."""
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=422, detail="question must not be empty")
        if app.state.graph is None:
            raise HTTPException(status_code=503, detail="triage graph is not ready")
        try:
            return run_triage(question, app.state.graph)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="triage failed") from exc

    return app


app = create_app()
