"""Live LangGraph tutor for fuzz / shrink / extract demos.

Set ``OPENAI_API_KEY`` before ``agent-spec-kit run`` on this directory.

The tutor exposes only ``multiply_integers(a, b)``; fuzzed scenarios send a mix of
valid multiplication prompts and off-topic lines so some trials fail strict
tool assertions.
"""

from __future__ import annotations

import os

import agent_spec_kit as ek
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

_LLM_MODEL_CASES = (
    ek.case("gpt-4.1-nano-2025-04-14", id="gpt41nano"),
    ek.case("gpt-5-nano", id="gpt5nano"),
)

_TUTOR_SYSTEM = (
    "You are a math tutor with one tool: multiply_integers(a, b). "
    "Whenever the user asks for a product of two integers, call multiply_integers "
    "with those integers (use argument names a and b). "
    "Then answer in plain language and include the numeric product as digits. "
    "If the user says something unrelated to multiplication, reply briefly that you "
    "can only help with integer products, and do not call tools."
)


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "langchain_fuzz_demo requires OPENAI_API_KEY (live-only example)."
        )


@tool
def multiply_integers(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


def _tutor_graph(llm_model: str) -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=llm_model, temperature=0)
    return create_react_agent(llm, [multiply_integers], prompt=_TUTOR_SYSTEM)


@ek.fixture
@ek.parametrize("llm_model", _LLM_MODEL_CASES)
async def adapted_agent(llm_model: str):
    graph = _tutor_graph(llm_model)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )
