"""API surface tests. Uses an injected fake graph so no model is loaded."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import create_app


def _client() -> TestClient:
    return TestClient(create_app(graph=object(), prewarm_startup=False))


def test_health_ok() -> None:
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_injected_graph_is_stored() -> None:
    sentinel = object()
    app = create_app(graph=sentinel, prewarm_startup=False)
    assert app.state.graph is sentinel
