"""Deterministic flagged-PO list tests (no LLM)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import create_app
from src.flagged import build_flagged_pos


def test_list_length_matches_queries_file() -> None:
    items = build_flagged_pos()
    assert len(items) == 13


def test_po_88405_fields() -> None:
    item = next(i for i in build_flagged_pos() if i.po_id == "PO-88405")
    assert item.supplier == "Anadolu Tekstil"
    assert item.tier == "V2"
    assert item.tier_display.number == 2
    assert item.tier_display.word == "Material"
    assert item.qty_variance_pct == -12.0
    assert item.eta_variance_days == 9
    assert item.summary_line == "Short-ship -12% \u00b7 ETA +9d"


def test_endpoint_returns_envelope() -> None:
    client = TestClient(create_app(graph=object(), prewarm_startup=False))
    response = client.get("/flagged-pos")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 13
    assert len(body["items"]) == 13
    assert body["items"][0]["po_id"].startswith("PO-")
