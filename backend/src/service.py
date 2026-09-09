"""Orchestrate one triage pass: invoke the graph and enrich the result for the UI."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage

from .api_schemas import TriageResponse
from .citations import resolve_citation

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<![\d])(?:\+|00|0)\d[\d\s().\-]{6,}\d(?![\d])")
_REDACTED = "[redacted]"


def _scrub_pii(text: str) -> str:
    """Redact email addresses and phone numbers from model-authored text."""
    return _PHONE_RE.sub(_REDACTED, _EMAIL_RE.sub(_REDACTED, text))


def run_triage(question: str, graph: Any) -> TriageResponse:
    """Run the compiled graph for one question and assemble the API response.

    :param question: The planner's verbatim question.
    :param graph: A compiled graph exposing ``invoke(state) -> dict``.
    :returns: The triage output, recommendation, resolved citations and halt.
    :raises RuntimeError: If the graph does not produce both structured outputs.
    """
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=question)],
            "final_output": None,
            "agent2_messages": [],
            "recommendation": None,
        }
    )

    triage = result.get("final_output")
    recommendation = result.get("recommendation")
    if triage is None or recommendation is None:
        raise RuntimeError("Triage did not complete: missing structured output.")

    # Defence in depth: never let model-authored text carry PII to the UI.
    recommendation.rationale = _scrub_pii(recommendation.rationale)
    if recommendation.escalation_target_role:
        recommendation.escalation_target_role = _scrub_pii(
            recommendation.escalation_target_role
        )

    citations = [resolve_citation(reference) for reference in recommendation.citations]
    return TriageResponse(
        triage=triage,
        recommendation=recommendation,
        citations=citations,
        halt=triage.halt,
    )
