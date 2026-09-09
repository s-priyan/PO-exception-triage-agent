"""Orchestrate one triage pass: invoke the graph and enrich the result for the UI."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from .api_schemas import TriageResponse
from .citations import resolve_citation


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

    citations = [resolve_citation(reference) for reference in recommendation.citations]
    return TriageResponse(
        triage=triage,
        recommendation=recommendation,
        citations=citations,
        halt=triage.halt,
    )
