"""Counterexample and structured failure types."""

from __future__ import annotations

import agent_spec_kit.match as m
from agent_spec_kit.match.api import tool_call
from agent_spec_kit.run import ConversationTurn, TurnResult
from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.failures import (
    FailureRecord,
    ScenarioAssertionFailed,
    conversation_turns_to_event_trace,
    counterexample_from_failure,
    raise_scenario_match_failure,
)


def test_counterexample_from_match_error() -> None:
    r = m.check(m.list([1, 2]), [1])
    assert not r.ok
    record = FailureRecord(
        scenario_name="t_example",
        step_index=2,
        step_kind="assert_tool_calls",
        turn_index=0,
        actual=[{"name": "x"}],
        matcher_spec=[1, 2],
        matcher_errors=r.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    assert "t_example" in cx.headline
    assert "step 2" in cx.location
    assert cx.path is not None


def test_counterexample_list_length_tool_calls_shows_counts_and_names() -> None:
    r = m.check(m.list([tool_call("a"), tool_call("b")], mode="ordered"), [{"name": "a"}])
    assert not r.ok
    record = FailureRecord(
        scenario_name="t_tools",
        step_index=1,
        step_kind="assert_tool_calls",
        turn_index=0,
        actual=[{"name": "a", "args": {}, "result": "1", "error": None, "children": [], "metadata": {}}],
        matcher_spec=[tool_call("a"), tool_call("b")],
        matcher_errors=r.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    assert "expected 2 tool call" in cx.expected_summary or "2" in cx.expected_summary
    assert "a" in cx.expected_summary and "b" in cx.expected_summary
    assert "agent recorded 1" in cx.actual_min
    assert cx.check_kind == "assert_tool_calls"


def test_counterexample_assert_that_uses_message_not_empty_tuple() -> None:
    record = FailureRecord(
        scenario_name="t_env",
        step_index=1,
        step_kind="assert_that",
        turn_index=0,
        actual=(),
        matcher_spec=None,
        matcher_errors=(),
        error=AssertionError("fixture X must be False"),
    )
    cx = counterexample_from_failure(record)
    assert "assert_that failed" in cx.expected_summary
    assert "fixture X" in cx.expected_summary
    assert "()" not in cx.actual_min
    assert "structured" in cx.actual_min.lower() or "fixture" in cx.actual_min.lower()


def test_raise_scenario_match_failure_raises_subclass() -> None:
    r = m.check(m.list([1]), [2])
    assert not r.ok
    try:
        raise_scenario_match_failure(
            scenario_name="s",
            step_index=0,
            step_kind="assert_output",
            turn_index=0,
            result=r,
            matcher_spec=1,
            actual=2,
            headline_prefix="assert_output",
        )
    except ScenarioAssertionFailed as e:
        assert e.counterexample.headline.startswith("assert_output:")
        assert e.record is not None
    else:
        raise AssertionError("expected ScenarioAssertionFailed")


def test_conversation_trace_includes_user_and_last_two_agent_turns() -> None:
    u0 = TurnResult(output="u0", events=())
    a0 = TurnResult(
        output="a0 out",
        events=(AgentTurnEvent(user_input="u0", agent_output="a0 out", children=[ToolCallEvent(tool_name="t0", result=0)]),),
    )
    u1 = TurnResult(output="u1", events=())
    a1 = TurnResult(
        output="a1 out",
        events=(AgentTurnEvent(user_input="u1", agent_output="a1 out", children=[ToolCallEvent(tool_name="t1", result=1)]),),
    )
    turns = (
        ConversationTurn.from_turn("user", u0),
        ConversationTurn.from_turn("agent", a0),
        ConversationTurn.from_turn("user", u1),
        ConversationTurn.from_turn("agent", a1),
    )
    roots = conversation_turns_to_event_trace(turns, max_agent_turns=5)
    assert len(roots) == 4
    from agent_spec_kit.events import UserTurnEvent

    assert isinstance(roots[0], UserTurnEvent) and roots[0].content == "u0"
    assert isinstance(roots[1], AgentTurnEvent) and roots[1].children[0].tool_name == "t0"
    assert isinstance(roots[2], UserTurnEvent) and roots[2].content == "u1"
    assert isinstance(roots[3], AgentTurnEvent) and roots[3].children[0].tool_name == "t1"


def test_conversation_trace_windows_last_five_agent_turns() -> None:
    """Earlier agent+user pair is dropped when more than 5 agent turns are present."""
    parts: list[ConversationTurn] = []
    for i in range(6):
        u = TurnResult(output=f"u{i}", events=())
        a = TurnResult(
            output=f"a{i}",
            events=(AgentTurnEvent(user_input=f"u{i}", agent_output=f"a{i}"),),
        )
        parts.append(ConversationTurn.from_turn("user", u))
        parts.append(ConversationTurn.from_turn("agent", a))
    roots = conversation_turns_to_event_trace(parts, max_agent_turns=5)
    labels = " ".join(r._rich_node_label() for r in roots)
    # Oldest full round (u0, a0) is dropped; window starts with u1.
    assert "u0" not in labels
    assert "u1" in labels
    assert "u5" in labels
