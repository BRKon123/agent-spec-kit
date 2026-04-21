"""Scenario specs against a LangGraph-wrapped agent (see ``fixtures.py``).

Expectations:
- ``test_arithmetic_reply_contains_five`` should **pass** (offline graph says "5";
  with ``OPENAI_API_KEY``, the react agent should still mention the sum for 2+3).
- The other two scenarios are **deliberately wrong** and should **fail**:
  wrong tool name, impossible exact output.
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "smoke"),
    timeout_s=120.0,
)
async def test_arithmetic_reply_contains_five(s, adapted_agent):
    s.user_message(
        "What is 2 + 3? If you use tools, use add_integers. "
        "Reply in natural language and include the digit 5 for the sum."
    )
    await s.materialise()
    out = str(s.last_turn.output)
    assert "5" in out, f"expected digit 5 in model output, got: {out!r}"


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "expected-failure"),
    timeout_s=120.0,
)
async def test_expects_nonexistent_sql_tool(s, adapted_agent):
    """Fails: no ``query_sql_database`` tool exists on this agent."""
    s.user_message("What is 2 + 3?")
    await s.materialise()
    s.assert_tool_calls(
        [m.tool_call("query_sql_database")],
        ordered=True,
        allow_extras=False,
    )
    await s.materialise()


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "expected-failure"),
    timeout_s=120.0,
)
async def test_expects_impossible_literal_output(s, adapted_agent):
    """Fails: model will not emit this exact token."""
    s.user_message("Say hello in one short sentence.")
    await s.materialise()
    s.assert_output("___LANGCHAIN_SCENARIO_IMPOSSIBLE_TOKEN___")
    await s.materialise()
