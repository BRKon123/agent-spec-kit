"""Shared LangGraph agent for scenario examples.

Uses a real ``create_react_agent`` + ``ChatOpenAI`` when ``OPENAI_API_KEY`` is set
(see ``examples/langchain_run_turn.py``). Otherwise builds a tiny compiled
``StateGraph`` that streams a fixed ``AIMessage`` so ``agent-spec-kit run`` works
offline without API keys.
"""

from __future__ import annotations

import os
from typing import Annotated, Any, TypedDict

import agent_spec_kit as ek
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent


class _OfflineState(TypedDict):
    messages: Annotated[list, add_messages]


def _offline_graph() -> object:
    """Minimal LangGraph app: one node, deterministic final assistant text."""

    def _reply(state: _OfflineState) -> dict[str, Any]:
        msgs = state.get("messages") or []
        last = msgs[-1] if msgs else None
        text = getattr(last, "content", "") if last is not None else ""
        if isinstance(text, str) and "2" in text and ("3" in text or "+" in text):
            body = "The answer is 5."
        else:
            body = f"Echo: {text!s}"
        return {"messages": [AIMessage(content=body)]}

    g: StateGraph[_OfflineState] = StateGraph(_OfflineState)
    g.add_node("assistant", _reply)
    g.add_edge(START, "assistant")
    g.add_edge("assistant", END)
    return g.compile()


@tool
def add_integers(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@tool
def multiply_integers(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


def _live_graph() -> object:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    return create_react_agent(llm, [add_integers, multiply_integers])


def _build_graph() -> object:
    if os.environ.get("OPENAI_API_KEY"):
        return _live_graph()
    return _offline_graph()


@ek.fixture
async def adapted_agent():
    graph = _build_graph()
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )
