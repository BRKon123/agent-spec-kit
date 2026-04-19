"""Live LangChain + OpenAI integration (skipped without API key)."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterable

import pytest
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from agent_spec_kit import AgentTurnEvent, ToolCallEvent
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


def _iter_tools_dfs(ev: object) -> Iterable[ToolCallEvent]:
    if isinstance(ev, ToolCallEvent):
        yield ev
    children = getattr(ev, "children", None) or []
    for c in children:
        yield from _iter_tools_dfs(c)


def _all_tools(events: tuple[object, ...]) -> list[ToolCallEvent]:
    return [t for root in events for t in _iter_tools_dfs(root)]


def _first_tool_result(events: tuple[object, ...], tool_name: str) -> object | None:
    for e in _all_tools(events):
        if e.tool_name == tool_name and e.error is None and e.result is not None:
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
        assert len(r.events) == 1
        assert isinstance(r.events[0], AgentTurnEvent)
        tool_names = [e.tool_name for e in _all_tools(r.events)]
        assert "add_integers" in tool_names
        assert "multiply_integers" in tool_names
        assert "secret_word" in tool_names
        assert _coerce_int(_first_tool_result(r.events, "add_integers")) == 42
        assert _coerce_int(_first_tool_result(r.events, "multiply_integers")) == 84
        assert "plugh" in str(r.output).lower() or any(
            "plugh" in str(e.result).lower()
            for e in _all_tools(r.events)
            if e.result is not None
        )

    asyncio.run(body())


class _ArithmeticReport(BaseModel):
    """Structured output from the specialist subagent."""

    sum_value: int = Field(description="Result of add_integers(10, 32)")
    product: int = Field(description="sum_value times 2")


@pytest.mark.skipif(not _has_openai(), reason="OPENAI_API_KEY not set")
def test_live_nested_create_agent_subagent_structured() -> None:
    """Nested create_agent: root AgentTurnEvent tree; delegate tool may contain inner tool events."""

    async def body() -> None:
        model = ChatOpenAI(
            model="gpt-5-nano",
            temperature=0.1,
            timeout=30,
        )

        @tool
        def add_integers_inner(a: int, b: int) -> int:
            """Add two integers and return the sum."""
            return a + b

        specialist = create_agent(
            model,
            tools=[add_integers_inner],
            response_format=_ArithmeticReport,
            system_prompt=(
                "You must call add_integers_inner with a=10 and b=32 exactly once. "
                "Set sum_value to that result and product to sum_value times 2."
            ),
        )

        @tool
        def run_specialist(task: str) -> str:
            """Delegate to the arithmetic specialist; returns JSON from its structured report."""
            out = specialist.invoke(
                {"messages": [{"role": "user", "content": task}]}
            )
            sr = out.get("structured_response")
            if sr is not None:
                if hasattr(sr, "model_dump_json"):
                    return sr.model_dump_json()
                return json.dumps(sr) if isinstance(sr, dict) else str(sr)
            last = out["messages"][-1]
            content = getattr(last, "content", last)
            return str(content)

        main_graph = create_agent(
            model,
            tools=[run_specialist],
            system_prompt=(
                "You have run_specialist. Call it once with the user's task verbatim "
                "so the specialist can produce the report."
            ),
        )

        adapted = wrap_langchain_agent(
            main_graph,
            lambda msg: {"messages": [HumanMessage(content=msg)]},
            stream_mode="updates",
            version="v2",
            subgraphs=True,
        )
        r = await adapted.run_turn(
            "Produce the arithmetic report: sum of 10 and 32, then product of that sum with 2."
        )
        assert r.status == "ok", r.error
        assert r.output is not None
        assert len(r.events) == 1
        root = r.events[0]
        assert isinstance(root, AgentTurnEvent)
        assert root.source_path == ()

        tool_names = [e.tool_name for e in _all_tools(r.events)]
        assert "run_specialist" in tool_names

        raw = _first_tool_result(r.events, "run_specialist")
        assert raw is not None
        text = raw if isinstance(raw, str) else str(raw)
        assert "42" in text and "84" in text

        outer = next(t for t in _all_tools(r.events) if t.tool_name == "run_specialist")
        inner_children = [c for c in outer.children if isinstance(c, ToolCallEvent)]
        inner_names = [c.tool_name for c in inner_children]
        if "add_integers_inner" in inner_names:
            assert _coerce_int(_first_tool_result(tuple(outer.children), "add_integers_inner")) == 42

    asyncio.run(body())
