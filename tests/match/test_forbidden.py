"""Tests for forbidden tool-call matcher."""

from __future__ import annotations

import agent_spec_kit.match as m
from agent_spec_kit.match.api import check


def test_forbid_single_tool_absent_passes() -> None:
    actual = [{"name": "heartbeat_ping", "args": {}}]
    from agent_spec_kit.match.api import forbidden_tool_calls_matcher

    spec = forbidden_tool_calls_matcher([m.tool_call("apply_bill_credit")])
    assert check(spec, actual).ok


def test_forbid_single_tool_present_fails() -> None:
    actual = [{"name": "apply_bill_credit", "args": {"amount": 10}}]
    from agent_spec_kit.match.api import forbidden_tool_calls_matcher

    spec = forbidden_tool_calls_matcher([m.tool_call("apply_bill_credit")])
    r = check(spec, actual)
    assert not r.ok
    assert r.errors[0].code == "forbidden_tool_call"


def test_forbid_ordered_subsequence_fails() -> None:
    from agent_spec_kit.match.api import forbidden_tool_calls_matcher

    actual = [
        {"name": "authenticate_customer", "args": {}},
        {"name": "apply_bill_credit", "args": {}},
    ]
    spec = forbidden_tool_calls_matcher(
        [m.tool_call("authenticate_customer"), m.tool_call("apply_bill_credit")],
        ordered=True,
    )
    r = check(spec, actual)
    assert not r.ok
    assert r.errors[0].code == "forbidden_tool_sequence"
