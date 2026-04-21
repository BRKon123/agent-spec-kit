"""Counterexample and structured failure types."""

from __future__ import annotations

import agent_spec_kit.match as m
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
