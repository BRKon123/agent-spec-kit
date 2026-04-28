"""Live-only LangGraph arithmetic agent for multiplication and addition.

Set ``OPENAI_API_KEY`` before running this example directory.
"""

from __future__ import annotations

import os

import agent_spec_kit as ek
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

_LLM_MODEL_CASES = (
    ek.case("gpt-5-nano", id="gpt5nano"),
)

_ARITHMETIC_SYSTEM = (
    "You are an arithmetic assistant with two tools only: "
    "multiply_numbers(a, b) and add_numbers(a, b). "
    "When asked to compute a mixed expression, call the tools step by step. "
    "Use multiply_numbers first when multiplication is required, then add_numbers. "
    "In your final response, include the intermediate multiplication result and the final total "
    "as digit strings."
)


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "langchain_arithmetic_llm_checks requires OPENAI_API_KEY "
            "(live-only example; no offline graph)."
        )


@tool
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


@tool
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


def _agent_graph(llm_model: str) -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=llm_model, temperature=0)
    return create_react_agent(llm, [multiply_numbers, add_numbers], prompt=_ARITHMETIC_SYSTEM)


@ek.fixture
@ek.parametrize("llm_model", _LLM_MODEL_CASES)
async def adapted_agent(llm_model: str):
    graph = _agent_graph(llm_model)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )
