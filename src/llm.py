"""LLM wrapper: binds tools for a gather loop and produces structured output.

A single wrapper serves both triage agents; each is constructed with its own tool
set and Pydantic output schema.
"""

from __future__ import annotations

import os
from typing import List, Sequence, Type

from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

DEFAULT_MODEL = "gpt-4o"


class StructuredToolLLM:
    """Wraps a chat model with tool binding and structured output.

    :param tools: Tools bound for the gather loop.
    :param output_schema: Pydantic model the final answer is coerced into.
    :param model: Optional model name; falls back to OPENAI_MODEL or the default.
    :param temperature: Sampling temperature; 0 for deterministic triage.
    """

    def __init__(
        self,
        tools: Sequence[BaseTool],
        output_schema: Type[BaseModel],
        model: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        model_name = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        base_model = ChatOpenAI(model=model_name, temperature=temperature)
        self._tool_model = base_model.bind_tools(list(tools))
        # function_calling keeps free-form record dicts intact for verbatim copy.
        self._structured_model = base_model.with_structured_output(
            output_schema, method="function_calling"
        )

    def invoke_tools(self, messages: List[BaseMessage]) -> BaseMessage:
        """Run the tool-bound model to gather facts or decide it is done."""
        return self._tool_model.invoke(messages)

    def finalize(self, messages: List[BaseMessage]) -> BaseModel:
        """Coerce the gathered context into the structured output object."""
        return self._structured_model.invoke(messages)
