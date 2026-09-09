"""Pydantic models for the HTTP API layer (separate from the agent schemas)."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel

from .schemas import HaltReason, Recommendation, TriageOutput

TierWord = Literal["Clean", "Minor", "Material", "Major", "Critical"]


class TierDisplay(BaseModel):
    """Human-facing tier label derived from the V0-V4 code."""

    number: int
    word: TierWord


class FlaggedPo(BaseModel):
    """One row in the flagged-PO list (deterministic; no LLM)."""

    po_id: str
    supplier: str
    category: str
    tier: Optional[str]
    tier_display: TierDisplay
    qty_variance_pct: Optional[float]
    eta_variance_days: Optional[int]
    summary_line: str
    query: str


class FlaggedPosResponse(BaseModel):
    """Envelope for the flagged-PO list."""

    count: int
    items: List[FlaggedPo]


class Citation(BaseModel):
    """A resolved SOP citation: code + section + title + quoted clause."""

    code: str
    section: str
    title: Optional[str] = None
    quote: Optional[str] = None


class TriageRequest(BaseModel):
    """Planner question payload."""

    question: str


class TriageResponse(BaseModel):
    """Full triage result returned to the UI."""

    triage: TriageOutput
    recommendation: Recommendation
    citations: List[Citation]
    halt: Optional[HaltReason] = None
