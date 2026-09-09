"""API surface tests. Uses an injected fake graph so no model is loaded."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from src.api import create_app
from src.schemas import Recommendation, TriageOutput
from src.service import run_triage


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


class _FakeGraph:
    """Stand-in graph that returns fixed structured outputs without an LLM."""

    def __init__(self, triage: TriageOutput, recommendation: Recommendation) -> None:
        self._triage = triage
        self._recommendation = recommendation
        self.last_state: dict = {}

    def invoke(self, state: dict) -> dict:
        self.last_state = state
        return {"final_output": self._triage, "recommendation": self._recommendation}


def _fake_success_graph() -> _FakeGraph:
    triage = TriageOutput(
        po_id="PO-88405",
        halt=None,
        planner_question="PO-88405 came in short and the ETA slipped, what's going on?",
        po_record={"po_id": "PO-88405", "ordered_qty": 5000, "confirmed_qty": 4400},
        forecast=None,
        tier={
            "tier": "V2",
            "qty_variance_pct": -12.0,
            "eta_variance_days": 9,
            "value_at_risk_gbp": 22800.0,
            "overrides_applied": [],
            "validation": {"passed": True, "failures": []},
        },
        exception_types=["quantity_variance_short", "eta_slip"],
        queries=["quantity variance amendment"],
    )
    recommendation = Recommendation(
        po_id="PO-88405",
        recommended_action="amend",
        rationale="V2 short-ship within amendment tolerance.",
        citations=["variance_detection_sop.md \u00a72.1"],
        confidence="high",
        escalation_target_role=None,
    )
    return _FakeGraph(triage, recommendation)


def test_triage_returns_enriched_citations() -> None:
    client = TestClient(
        create_app(graph=_fake_success_graph(), prewarm_startup=False)
    )
    response = client.post("/triage", json={"question": "PO-88405?"})
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"]["recommended_action"] == "amend"
    assert body["halt"] is None
    assert body["citations"][0]["code"] == "MERCH-SOP-014"
    assert body["citations"][0]["title"] == "Compound variance rule"
    assert body["citations"][0]["section"] == "\u00a72.1"
    assert body["citations"][0]["quote"] is not None


def test_triage_rejects_empty_question() -> None:
    client = TestClient(
        create_app(graph=_fake_success_graph(), prewarm_startup=False)
    )
    response = client.post("/triage", json={"question": "   "})
    assert response.status_code == 422


def test_triage_passes_question_into_graph() -> None:
    graph = _fake_success_graph()
    client = TestClient(create_app(graph=graph, prewarm_startup=False))
    client.post("/triage", json={"question": "hello PO-88405"})
    sent = graph.last_state["messages"][0]
    assert isinstance(sent, HumanMessage)
    assert sent.content == "hello PO-88405"


def test_triage_returns_503_when_no_graph() -> None:
    client = TestClient(create_app(graph=None, prewarm_startup=False))
    response = client.post("/triage", json={"question": "PO-88405?"})
    assert response.status_code == 503


def test_run_triage_raises_when_outputs_missing() -> None:
    class _EmptyGraph:
        def invoke(self, state: dict) -> dict:
            return {"final_output": None, "recommendation": None}

    with pytest.raises(RuntimeError):
        run_triage("PO-88405?", _EmptyGraph())


def test_triage_maps_graph_failure_to_502_with_cors() -> None:
    class _ExplodingGraph:
        def invoke(self, state: dict) -> dict:
            raise RuntimeError("boom")

    client = TestClient(
        create_app(graph=_ExplodingGraph(), prewarm_startup=False),
        raise_server_exceptions=False,
    )
    response = client.post(
        "/triage",
        json={"question": "PO-88405?"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 502
    header_keys = {key.lower() for key in response.headers.keys()}
    assert "access-control-allow-origin" in header_keys


def test_run_triage_scrubs_pii_from_recommendation() -> None:
    triage = TriageOutput(
        po_id="PO-1",
        halt=None,
        planner_question="q",
        po_record={},
        forecast=None,
        tier=None,
        exception_types=[],
        queries=[],
    )
    rec = Recommendation(
        po_id="PO-1",
        recommended_action="escalate",
        rationale="Email a.b@example.com or call 07700 900142 now.",
        citations=[],
        confidence="low",
        escalation_target_role="Manager j@x.co",
    )
    out = run_triage("q", _FakeGraph(triage, rec))
    assert "a.b@example.com" not in out.recommendation.rationale
    assert "07700 900142" not in out.recommendation.rationale
    assert "@" not in (out.recommendation.escalation_target_role or "")
