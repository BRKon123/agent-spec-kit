"""Multiplication tutor scenarios (scripted turns vs simulated student).

Requires ``OPENAI_API_KEY`` and the LangChain stack (``dependency-groups`` dev).

Each scenario is expanded over two model cases from ``fixtures.py`` (``llm_model``).

Run from repo root::

    OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_multiply_dialog/
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "multiply-dialog", "smoke"),
    timeout_s=120.0,
)
async def test_multiply_dialog_scripted_user_messages(s):
    """Two explicit user turns; after each, require multiply_integers and the product."""
    (
        s.user_message(
            "What is 5 times 6? Use multiply_integers with a=5 and b=6 only, then reply briefly "
            "and include the digit sequence for the product."
        )
        .assert_tool_calls(
            [m.tool_call("multiply_integers", args={"a": 5, "b": 6})],
            ordered=True,
            allow_extras=True,
        )
        .assert_output(m.contains("30"))
        .user_message(
            "What is 9 times 8? Use multiply_integers with a=9 and b=8 only, then reply briefly "
            "and include the digit sequence for the product."
        )
        .assert_tool_calls(
            [m.tool_call("multiply_integers", args={"a": 9, "b": 8})],
            ordered=True,
            allow_extras=True,
        )
        .assert_output(m.contains("72"))
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    user_fixture="user_simulator",
    repeats=1,
    tags=("langchain", "example", "multiply-dialog", "simulation"),
    timeout_s=180.0,
)
async def test_multiply_dialog_simulated_student(s):
    """Student model asks 4×5 then 3×8; after each tutor reply, assert tool use and product."""
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input="Session start. Produce only your first question.",
            max_turns=1,
        )
        .assert_tool_calls(
            [m.tool_call("multiply_integers", args={"a": 4, "b": 5})],
            ordered=True,
            allow_extras=True,
            actor="agent",
        )
        .assert_output(m.one_of(m.contains("20"), m.contains("twenty")), actor="agent")
        .simulate_conversation(max_turns=1)
        .assert_tool_calls(
            [m.tool_call("multiply_integers", args={"a": 3, "b": 9})],
            ordered=True,
            allow_extras=True,
            actor="agent",
        )
        .assert_output(m.contains("24"), actor="agent")
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    user_fixture="user_simulator_with_tools",
    repeats=1,
    tags=("langchain", "example", "multiply-dialog", "simulation", "user-tools"),
    timeout_s=180.0,
)
async def test_multiply_dialog_simulated_student_user_tools(s):
    """Like simulated student, but the student agent calls ``student_checkpoint`` each turn."""
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input="Session start. Produce only your first question.",
            max_turns=1,
        )
        .assert_tool_calls(
            [m.tool_call("student_checkpoint")],
            ordered=True,
            allow_extras=True,
            actor="user",
        )
        .assert_tool_calls(
            [m.tool_call("multiply_integers", args={"a": 4, "b": 5})],
            ordered=True,
            allow_extras=True,
            actor="agent",
        )
        .assert_output(m.one_of(m.contains("20"), m.contains("twenty")), actor="agent")
        .simulate_conversation(max_turns=1)
        .assert_tool_calls(
            [m.tool_call("student_checkpoint")],
            ordered=True,
            allow_extras=True,
            actor="user",
        )
        .assert_tool_calls(
            [m.tool_call("multiply_integers", args={"a": 3, "b": 8})],
            ordered=True,
            allow_extras=True,
            actor="agent",
        )
        .assert_output(m.contains("24"), actor="agent")
    )
