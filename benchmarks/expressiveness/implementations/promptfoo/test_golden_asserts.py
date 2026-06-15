"""Smoke tests: Promptfoo python asserts + trajectory span builder on golden traces."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from agentevals.trajectory.match import create_trajectory_match_evaluator

from implementations.langsmith.trajectory_bridge import reference_messages_for_tools, trace_to_messages
from implementations.promptfoo.assert_c11 import get_assert as assert_c11
from implementations.promptfoo.assert_c12 import get_assert as assert_c12
from implementations.promptfoo.trace_spans import frozen_trace_to_promptfoo_trace
from shared.trace_io import load_trace


def _trajectory_in_order(trace: dict, steps: list[str], *, turn: str | None = None) -> bool:
    """Mirror promptfoo trajectory:tool-sequence in_order via agentevals superset + order walk."""
    act = trace_to_messages(trace, turn=turn)
    ref = reference_messages_for_tools([{"name": s, "args": {}} for s in steps])
    has_steps = create_trajectory_match_evaluator(
        trajectory_match_mode="superset", tool_args_match_mode="ignore"
    )(outputs=act, reference_outputs=ref)["score"]
    tools = (trace.get("turns") or [])[-1].get("tools") if turn == "last" else trace.get("tools")
    names = [str(t.get("name", "")) for t in tools or []]
    ei = 0
    for name in names:
        if ei < len(steps) and name == steps[ei]:
            ei += 1
    return bool(has_steps) and ei == len(steps)


def test_c05_trajectory_sequence():
    trace = load_trace("C05")
    assert _trajectory_in_order(trace, ["authenticate_customer", "get_outage_status"])


def test_c07_trajectory_args():
    trace = load_trace("C07")
    pf = frozen_trace_to_promptfoo_trace(trace, "C07")
    names = [
        s.get("attributes", {}).get("tool.name")
        for s in pf["spans"]
        if s.get("attributes", {}).get("tool.name")
    ]
    assert "authenticate_customer" in names and "get_line_status" in names


def test_c10_trajectory_tools_used():
    trace = load_trace("C10")
    pf = frozen_trace_to_promptfoo_trace(trace, "C10")
    names = {s.get("attributes", {}).get("tool.name") for s in pf["spans"]}
    assert {"heartbeat_ping", "get_line_status"} <= names


def test_c11_c12_python_asserts():
    for check_id, fn in [("C11", assert_c11), ("C12", assert_c12)]:
        out = json.dumps(load_trace(check_id))
        assert fn(out, {}) is True, check_id


def test_c12_trajectory_and_store():
    trace = load_trace("C12")
    assert _trajectory_in_order(
        trace,
        ["authenticate_customer", "create_support_ticket"],
        turn="last",
    )
    assert assert_c12(json.dumps(trace), {}) is True
