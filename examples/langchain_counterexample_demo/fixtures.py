"""Live-only LangGraph React agent for the counterexample CLI demo.

This example **does not** provide an offline graph: set ``OPENAI_API_KEY`` before
running ``agent-spec-kit run`` on this directory.
"""

from __future__ import annotations

import os

import agent_spec_kit as ek
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "langchain_counterexample_demo requires OPENAI_API_KEY "
            "(live-only example; no offline graph)."
        )


@tool
def add_integers(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@tool
def multiply_integers(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


def _live_graph() -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    return create_react_agent(llm, [add_integers, multiply_integers])


@ek.fixture
async def adapted_agent():
    graph = _live_graph()
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )


@ek.fixture
def wrong_expected_substring() -> str:
    """Token the live model will not place in normal short replies (for body asserts)."""
    return "___COUNTEREX_DEMO_TOKEN_NEVER_IN_OUTPUT___"


@ek.fixture
def env_flag_true() -> bool:
    """Always true; paired with ``assert_that`` to simulate a failing env invariant."""
    return True
