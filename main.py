"""Command-line entry point for the PO exception triage system.

Usage:
    python main.py 

Runs Agent 1 (triage) then Agent 2 (grounded recommendation) and prints both.
"""

from __future__ import annotations

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from src.graph import build_triage_graph
from src.retrieval import prewarm

DEFAULT_QUESTION = (
    "PO-88405 has come in short of what we ordered and the ETA has slipped, "
    "what's going on?"
)


def main() -> None:
    """Run one end-to-end triage pass and print both structured outputs."""
    load_dotenv()

    prewarm()  # load the embedding model and build/load the SOP index once
    graph = build_triage_graph()

    while True:
        question = input("Enter a question: ") or DEFAULT_QUESTION

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

        print("=== Agent 1 - triage ===")
        print(triage.model_dump_json(indent=2))
        print("\n=== Agent 2 - recommendation ===")
        print(recommendation.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
