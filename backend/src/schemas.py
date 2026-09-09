"""Pydantic schemas for the PO exception triage agent (Agent 1)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ExceptionType = Literal[
    "quantity_variance_short",
    "quantity_variance_over",
    "eta_slip",
    "partial_delivery",
    "season_boundary_risk",
    "wholesale_constraint",
    "parent_child_context",
]

HaltReason = Literal["unresolved_po", "data_quality", "terminal_status"]


class ValidationResult(BaseModel):
    """Outcome of the SOP data-quality checks (MERCH-SOP-014 section 4)."""

    passed: bool = Field(description="True when the record can be reasoned over.")
    failures: List[str] = Field(
        default_factory=list,
        description="Human-readable reasons the record failed validation.",
    )


class TierResult(BaseModel):
    """Authoritative output of compute_variance_tier."""

    tier: str = Field(description="Severity tier label, V0 through V4.")
    qty_variance_pct: Optional[float] = Field(
        default=None,
        description="Signed quantity variance percentage, or null when not computable.",
    )
    eta_variance_days: Optional[int] = Field(
        default=None,
        description="Signed ETA variance in calendar days, or null when not computable.",
    )
    value_at_risk_gbp: Optional[float] = Field(
        default=None,
        description="Absolute value at risk in GBP, or null when not computable.",
    )
    overrides_applied: List[str] = Field(
        default_factory=list,
        description="SOP overrides that changed the base tier.",
    )
    validation: ValidationResult


class TriageOutput(BaseModel):
    """The single object Agent 1 emits. Tool output is copied verbatim."""

    po_id: Optional[str] = Field(
        default=None, description="Resolved PO identifier, or null if unresolved."
    )
    halt: Optional[HaltReason] = Field(
        default=None,
        description="Halt reason, or null when triage completes normally.",
    )
    planner_question: str = Field(
        description="The planner's original wording, unmodified."
    )
    po_record: Optional[Dict[str, Any]] = Field(
        default=None, description="Verbatim copy of get_purchase_order output."
    )
    forecast: Optional[Dict[str, Any]] = Field(
        default=None, description="Verbatim copy of get_forecast output."
    )
    tier: Optional[Dict[str, Any]] = Field(
        default=None, description="Verbatim copy of compute_variance_tier output."
    )
    exception_types: List[ExceptionType] = Field(
        default_factory=list,
        description="Every label the record supports. Empty on halt.",
    )
    queries: List[str] = Field(
        default_factory=list,
        description="Two to four topic phrases for Agent 2. Empty on halt.",
    )


RecommendedAction = Literal[
    "amend",
    "split_child_po",
    "firm_planned_order",
    "raise_backorder",
    "escalate",
]

Confidence = Literal["high", "medium", "low"]


class Recommendation(BaseModel):
    """Agent 2's grounded recommendation for the PO exception."""

    po_id: Optional[str] = Field(default=None, description="PO identifier from Agent 1.")
    recommended_action: RecommendedAction = Field(
        description="Exactly one action from the defined set."
    )
    rationale: str = Field(
        description="Short, factual justification grounded in the cited clauses."
    )
    citations: List[str] = Field(
        default_factory=list,
        description='SOP clauses relied on, each as "document.md \u00a7n".',
    )
    confidence: Confidence = Field(description="Retrieval-grounded confidence level.")
    escalation_target_role: Optional[str] = Field(
        default=None,
        description="Role title only (never a person), or null when no escalation.",
    )
