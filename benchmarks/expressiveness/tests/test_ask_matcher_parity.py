"""Verify agent_spec_kit matchers accept the same golden traces as canonical_checks."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

import agent_spec_kit.match as m
from agent_spec_kit.match.api import check

from specimens.messages import meta
from shared.canonical_checks import CHECK_BY_ID
from shared.store_sim import insert_ticket
from shared.trace_helpers import walk_root_tools
from shared.trace_io import load_trace

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


def _tools(trace: dict) -> list:
    return walk_root_tools(trace)


def _last_turn_tools(trace: dict) -> list:
    turns = trace.get("turns") or []
    assert turns
    return walk_root_tools(turns[-1])


def test_c01_output_matcher_matches_canonical():
    trace = load_trace("C01")
    spec = m.all_of(
        m.one_of(m.contains("credit"), m.contains("refund")),
        m.one_of(m.contains("$"), m.contains("dollar")),
    )
    assert check(spec, trace["output"]).ok
    assert CHECK_BY_ID["C01"](trace)


def test_c02_tool_matcher_matches_canonical():
    trace = load_trace("C02")
    spec = m.list(
        [
            m.tool_call(
                "run_network_diagnostics_specialist",
                result=m.object(
                    {
                        "severity": m.one_of("high"),
                        "recommended_action": m.one_of("create_ticket"),
                        "escalation_reason": m.string(min_len=1),
                    },
                    extra="forbid",
                ),
            ),
        ],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C02"](trace)


def test_c03_conditional_matcher_matches_canonical():
    trace = load_trace("C03")
    spec = m.list(
        [
            m.tool_call(
                "run_billing_policy_specialist",
                result=m.object(
                    {
                        "eligible": m.one_of(True, False),
                        "amount": m.optional(m.number(min=0.01)),
                        "currency": m.optional(m.string()),
                    },
                    extra="forbid",
                    rules=[
                        m.require("amount").when(m.field("eligible") == True),
                        m.forbid("amount").when(m.field("eligible") == False),
                    ],
                ),
            ),
        ],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C03"](trace)


def test_c04_numeric_matcher_matches_canonical():
    trace = load_trace("C04")
    spec = m.list(
        [
            m.tool_call(
                "run_billing_policy_specialist",
                result=m.object(
                    {"eligible": True, "amount": m.number(min=0.01, max=500.0)},
                    extra="forbid",
                ),
            ),
        ],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C04"](trace)


def test_c05_ordered_matcher_matches_canonical():
    trace = load_trace("C05")
    spec = m.list(
        [m.tool_call("authenticate_customer"), m.tool_call("get_outage_status")],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C05"](trace)


def test_c06_forbidden_matcher_matches_canonical():
    trace = load_trace("C06")
    spec = m.list([m.tool_call("apply_bill_credit")], mode="ordered", allow_extras=True)
    assert not check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C06"](trace)


def test_c07_tool_args_matcher_matches_canonical():
    trace = load_trace("C07")
    mmeta = meta()
    spec = m.list(
        [
            m.tool_call("authenticate_customer"),
            m.tool_call(
                "get_line_status",
                args=m.object({"line_id": mmeta["line_id"]}, extra="forbid"),
            ),
        ],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C07"](trace)


def test_c08_tool_result_matcher_matches_canonical():
    trace = load_trace("C08")
    spec = m.list(
        [
            m.tool_call(
                "run_network_diagnostics_specialist",
                result=m.object(
                    {
                        "severity": m.one_of("medium", "high"),
                        "recommended_action": m.string(min_len=1),
                        "summary": m.string(min_len=10),
                    },
                    extra="forbid",
                ),
            ),
        ],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C08"](trace)


def test_c09_nested_matcher_matches_canonical():
    trace = load_trace("C09")
    spec = m.list(
        [
            m.tool_call(
                "run_network_diagnostics_specialist",
                children=[
                    m.tool_call("pull_network_events"),
                    m.tool_call("score_signal_anomaly"),
                ],
            ),
        ],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C09"](trace)


def test_c10_unordered_matcher_matches_canonical():
    trace = load_trace("C10")
    spec = m.list(
        [m.tool_call("heartbeat_ping"), m.tool_call("get_line_status")],
        mode="unordered",
        allow_extras=True,
    )
    assert check(spec, _tools(trace)).ok
    assert CHECK_BY_ID["C10"](trace)


def test_c11_db_state_matches_canonical():
    trace = load_trace("C11")
    base = Path(tempfile.mkdtemp(prefix="parity_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        o.assert_ticket_exists(telco)
        assert CHECK_BY_ID["C11"](trace)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_c12_multi_turn_matches_canonical():
    trace = load_trace("C12")
    mmeta = meta()
    spec = m.list(
        [m.tool_call("authenticate_customer"), m.tool_call("create_support_ticket")],
        mode="ordered",
        allow_extras=True,
    )
    assert check(spec, _last_turn_tools(trace)).ok
    base = Path(tempfile.mkdtemp(prefix="parity_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=mmeta["line_id"], ticket_id="INC-9046")
        o.assert_ticket_for_line(telco, mmeta["line_id"])
        assert CHECK_BY_ID["C12"](trace)
    finally:
        shutil.rmtree(base, ignore_errors=True)
