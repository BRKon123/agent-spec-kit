"""Live Pydantic AI + OpenAI integration (skipped without API key)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterable

import pytest
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from agent_spec_kit import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.integrations.pydantic_ai_adapter import wrap_pydantic_ai_agent

pytestmark = pytest.mark.integration


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
def test_live_agent_tool_and_output() -> None:
    agent = Agent(
        "openai:gpt-5-nano",
        system_prompt=(
            "You have three tools: add_integers, multiply_integers, secret_word. "
            "Call them when the user asks for arithmetic or the secret word."
        ),
        model_settings={"temperature": 0},
    )

    @agent.tool
    async def add_integers(ctx: RunContext, a: int, b: int) -> int:
        """Add two integers and return the sum."""
        return a + b

    @agent.tool
    async def multiply_integers(ctx: RunContext, a: int, b: int) -> int:
        """Multiply two integers and return the product."""
        return a * b

    @agent.tool
    async def secret_word(ctx: RunContext) -> str:
        """Return the secret test word."""
        return "plugh"

    async def body() -> None:
        adapted = wrap_pydantic_ai_agent(agent)
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
    sum_value: int = Field(description="Sum of 10 and 32")
    product: int = Field(description="sum_value times 2")


@pytest.mark.skipif(not _has_openai(), reason="OPENAI_API_KEY not set")
def test_live_nested_agent_structured_tool_result() -> None:
    """Outer agent: parallel outer tools are siblings under root; inner tool may nest under run_analyst."""

    inner = Agent(
        "openai:gpt-5-nano",
        output_type=_ArithmeticReport,
        system_prompt=(
            "You have add_inner. Call add_inner(10, 32) once. "
            "Your final output must have sum_value equal to that sum and product equal to sum_value*2."
        ),
        model_settings={"temperature": 0},
    )

    @inner.tool
    async def add_inner(ctx: RunContext, a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    outer = Agent(
        "openai:gpt-5-nano",
        system_prompt=(
            "You have run_analyst and sidecar_ping. When the user asks for the arithmetic report, "
            "you MUST call BOTH tools in the same step (parallel tool calls): "
            "(1) run_analyst with the user's message as task, (2) sidecar_ping with no arguments. "
            "Then answer using the analyst result."
        ),
        model_settings={"temperature": 0},
    )

    @outer.tool
    async def run_analyst(ctx: RunContext, task: str) -> _ArithmeticReport:
        """Run the specialist and return its structured report."""
        result = await inner.run(task)
        assert result.output is not None
        return result.output

    @outer.tool
    async def sidecar_ping(ctx: RunContext) -> str:
        """Parallel sidecar for nested demo."""
        return "parallel-sidecar-ok"

    async def body() -> None:
        adapted = wrap_pydantic_ai_agent(outer)
        r = await adapted.run_turn(
            "Produce the arithmetic report: sum of 10 and 32, then twice that sum. "
            "Call run_analyst and sidecar_ping together."
        )
        assert r.status == "ok", r.error
        assert r.output is not None
        assert len(r.events) == 1
        root = r.events[0]
        assert isinstance(root, AgentTurnEvent)
        tool_names = [e.tool_name for e in _all_tools(r.events)]
        assert "run_analyst" in tool_names
        assert "sidecar_ping" in tool_names
        raw = _first_tool_result(r.events, "run_analyst")
        assert raw is not None
        if isinstance(raw, _ArithmeticReport):
            assert raw.sum_value == 42
            assert raw.product == 84
        elif isinstance(raw, dict):
            assert int(raw.get("sum_value", -1)) == 42
            assert int(raw.get("product", -1)) == 84
        else:
            s = str(raw).lower()
            assert "42" in s and "84" in s

        root_tool_children = [c for c in root.children if isinstance(c, ToolCallEvent)]
        root_tool_names = {c.tool_name for c in root_tool_children}
        assert "run_analyst" in root_tool_names
        assert "sidecar_ping" in root_tool_names
        run_analyst_node = next(t for t in root_tool_children if t.tool_name == "run_analyst")
        nested_under_analyst = {
            c.tool_name for c in run_analyst_node.children if isinstance(c, ToolCallEvent)
        }
        assert "sidecar_ping" not in nested_under_analyst

        outer_tool = run_analyst_node
        inner_children = [c for c in outer_tool.children if isinstance(c, ToolCallEvent)]
        inner_names = [c.tool_name for c in inner_children]
        if "add_inner" in inner_names:
            assert _coerce_int(_first_tool_result(tuple(outer_tool.children), "add_inner")) == 42

    asyncio.run(body())
