"""Build agent-spec-kit Counterexample objects for expressiveness fail traces."""

from __future__ import annotations

from typing import Any

import agent_spec_kit.match as m
from agent_spec_kit.failures import Counterexample, FailureRecord, counterexample_from_failure
from agent_spec_kit.match.api import check, forbidden_tool_calls_matcher

from shared.ask_specs import output_spec, tools_spec
from shared.fail_traces import fail_trace_for
from shared.trace_helpers import walk_root_tools


def _step_kind_for(check_id: str) -> str:
    if check_id == "C01":
        return "assert_output"
    if check_id == "C06":
        return "forbid_tool_calls"
    if check_id == "C11":
        return "assert_that"
    return "assert_tool_calls"


def _actual_and_spec(check_id: str, trace: dict[str, Any]) -> tuple[Any, Any]:
    if check_id == "C01":
        return trace.get("output", ""), output_spec("C01")
    if check_id == "C06":
        actual = walk_root_tools(trace)
        spec = forbidden_tool_calls_matcher([m.tool_call("apply_bill_credit")], ordered=True)
        return actual, spec
    if check_id == "C12":
        turns = trace.get("turns") or []
        actual = walk_root_tools(turns[-1]) if turns else []
        spec = tools_spec(check_id)
        return actual, spec
    actual = walk_root_tools(trace)
    spec = tools_spec(check_id)
    return actual, spec


def ask_counterexample_for_check(check_id: str) -> Counterexample:
    """Run the ask matcher on the intentional fail trace and return a Counterexample."""
    trace = fail_trace_for(check_id)
    actual, spec = _actual_and_spec(check_id, trace)
    if spec is None:
        raise ValueError(f"no ask spec for {check_id}")
    result = check(spec, actual)
    if result.ok:
        raise RuntimeError(f"fail trace unexpectedly passed {check_id}")
    record = FailureRecord(
        scenario_name=f"test_{check_id.lower()}_fail",
        step_index=1,
        step_kind=_step_kind_for(check_id),
        turn_index=0,
        actual=actual,
        matcher_spec=spec,
        matcher_errors=result.errors,
        turn_results=None,
        assertion_index_after_turn=1,
    )
    return counterexample_from_failure(record)
