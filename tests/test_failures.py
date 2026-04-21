"""Counterexample and structured failure types."""

from __future__ import annotations

import agent_spec_kit.match as m
from agent_spec_kit.match.api import tool_call
from agent_spec_kit.failures import (
    FailureRecord,
    ScenarioAssertionFailed,
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
