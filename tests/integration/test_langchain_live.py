"""Live LangChain + OpenAI integration (skipped without API key)."""

from __future__ import annotations

import asyncio
import os

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent_spec_kit import ToolCallEvent
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

pytestmark = pytest.mark.integration


@tool
def add_integers(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@tool
def multiply_integers(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


@tool
def secret_word() -> str:
    """Return the secret test word."""
    return "plugh"


def _has_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _first_tool_result(events: list[object], tool_name: str) -> object | None:
    for e in events:
        if isinstance(e, ToolCallEvent) and e.tool_name == tool_name and e.error is None:
            if e.result is not None:
                return e.result
    return None


@pytest.mark.skipif(not _has_openai(), reason="OPENAI_API_KEY not set")
def test_live_react_agent_tool_and_output() -> None:
    async def body() -> None:
        llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
        graph = create_react_agent(llm, [add_integers, multiply_integers, secret_word])
        adapted = wrap_langchain_agent(
            graph,
            lambda msg: {"messages": [HumanMessage(content=msg)]},
            stream_mode="updates",
            version="v2",
        )
        r = await adapted.run_turn(
            "You have add_integers, multiply_integers, and secret_word. "
            "1) Call add_integers with a=10 and b=32. "
            "2) Call multiply_integers with a equal to that sum and b=2. "
            "3) Call secret_word exactly once. "
            "4) Reply with one line: the sum, a space, the product, a space, the secret word."
        )
        assert r.status == "ok", r.error
        assert r.output is not None
        tool_names = [e.tool_name for e in r.events if isinstance(e, ToolCallEvent)]
        assert "add_integers" in tool_names
        assert "multiply_integers" in tool_names
        assert "secret_word" in tool_names
        assert _coerce_int(_first_tool_result(r.events, "add_integers")) == 42
        assert _coerce_int(_first_tool_result(r.events, "multiply_integers")) == 84
        assert "plugh" in str(r.output).lower() or any(
            "plugh" in str(e.result).lower()
            for e in r.events
            if isinstance(e, ToolCallEvent) and e.result is not None
        )

    asyncio.run(body())
