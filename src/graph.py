"""LangGraph wiring for the two-stage PO exception triage system.

Graph shape:

    START -> agent1 -> (tools1 -> agent1)* -> agent2 -> (tools2 -> agent2)* -> END

- agent1 (Agent 1) gathers facts with the data tools and emits the TriageOutput.
- agent2 (Agent 2) receives that output, retrieves SOP passages with search_sops,
  and emits the grounded Recommendation.

Each agent node is a StructuredToolLLM: it binds its tools for the gather loop and,
once no further tool call is needed, produces its structured output.
"""

from __future__ import annotations

from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .llm import StructuredToolLLM
from .prompts import AGENT_1_SYSTEM_PROMPT, AGENT_2_SYSTEM_PROMPT
from .retrieval import search_sops
from .schemas import Recommendation, TriageOutput
from .tools import TRIAGE_TOOLS


class TriageState(TypedDict):
    """Graph state spanning both agents.

    :param messages: Agent 1 conversation.
    :param final_output: Agent 1's structured triage object.
    :param agent2_messages: Agent 2 conversation.
    :param recommendation: Agent 2's structured recommendation.
    """

    messages: Annotated[List[AnyMessage], add_messages]
    final_output: Optional[TriageOutput]
    agent2_messages: Annotated[List[AnyMessage], add_messages]
    recommendation: Optional[Recommendation]


def build_triage_graph(
    agent1_llm: Optional[StructuredToolLLM] = None,
    agent2_llm: Optional[StructuredToolLLM] = None,
):
    """Compile and return the two-stage triage graph.

    :param agent1_llm: Optional Agent 1 wrapper; a default is created otherwise.
    :param agent2_llm: Optional Agent 2 wrapper; a default is created otherwise.
    :returns: The compiled LangGraph application.
    """
    agent1_llm = agent1_llm or StructuredToolLLM(TRIAGE_TOOLS, TriageOutput)
    agent2_llm = agent2_llm or StructuredToolLLM([search_sops], Recommendation)

    def agent1(state: TriageState) -> dict:
        conversation = [SystemMessage(content=AGENT_1_SYSTEM_PROMPT), *state["messages"]]
        response = agent1_llm.invoke_tools(conversation)
        if response.tool_calls:
            return {"messages": [response]}
        # No further tool call: gathering is done, so emit the triage object.
        return {"messages": [response], "final_output": agent1_llm.finalize(conversation)}

    def route_agent1(state: TriageState) -> str:
        if state.get("final_output") is not None:
            return "agent2"
        # Still holds pending tool calls, so execute them.
        return "tools1"

    def agent2(state: TriageState) -> dict:
        history = state.get("agent2_messages") or []
        emitted: List[AnyMessage] = []
        if not history:
            # First entry: seed the conversation with Agent 1's output.
            handoff = HumanMessage(content=state["final_output"].model_dump_json(indent=2))
            history = [handoff]
            emitted.append(handoff)

        conversation = [SystemMessage(content=AGENT_2_SYSTEM_PROMPT), *history]
        response = agent2_llm.invoke_tools(conversation)
        emitted.append(response)
        if response.tool_calls:
            return {"agent2_messages": emitted}
        # Retrieval is done, so emit the grounded recommendation.
        recommendation = agent2_llm.finalize(conversation)
        return {"agent2_messages": emitted, "recommendation": recommendation}

    def route_agent2(state: TriageState) -> str:
        if state.get("recommendation") is not None:
            return END
        # Still holds pending tool calls, so execute them.
        return "tools2"

    builder = StateGraph(TriageState)
    builder.add_node("agent1", agent1)
    builder.add_node("tools1", ToolNode(TRIAGE_TOOLS))
    builder.add_node("agent2", agent2)
    builder.add_node("tools2", ToolNode([search_sops], messages_key="agent2_messages"))

    builder.add_edge(START, "agent1")
    builder.add_conditional_edges(
        "agent1", route_agent1, {"tools1": "tools1", "agent2": "agent2"}
    )
    builder.add_edge("tools1", "agent1")
    builder.add_conditional_edges("agent2", route_agent2, {"tools2": "tools2", END: END})
    builder.add_edge("tools2", "agent2")
    return builder.compile()
