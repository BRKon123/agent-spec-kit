"""Plain pytest — inlined check logic in CHECK regions (LOC benchmark)."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from specimens.messages import meta
from shared.store_sim import insert_ticket
from shared.trace_helpers import (
    any_forbidden_present,
    find_tool,
    nested_children,
    ordered_subsequence,
    tool_names,
    unordered_set,
    walk_root_tools,
)

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402

from shared.trace_io import load_trace

_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})
_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})

def test_c01_output_rubric():
    trace = load_trace("C01")
    # CHECK_START
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    assert topic and money
    # CHECK_END

def test_c02_object_shape():
    trace = load_trace("C02")
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        assert False
    r = tool.get("result")
    if not isinstance(r, dict):
        assert False
    keys = set(r.keys())
    if keys != _C02_REQUIRED_KEYS:
        assert False
    ok = (
        r.get("severity") == "high"
        and r.get("recommended_action") == "create_ticket"
        and len(str(r.get("escalation_reason", ""))) >= 1
    )
    assert ok
    # CHECK_END

def test_c03_conditional_object():
    trace = load_trace("C03")
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        assert False
    r = tool.get("result")
    if not isinstance(r, dict) or "eligible" not in r:
        assert False
    if r.get("eligible"):
        assert "amount" in r and float(r["amount"]) > 0
    else:
        assert "amount" not in r
    # CHECK_END

def test_c04_numeric_regex():
    trace = load_trace("C04")
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        assert False
    r = tool.get("result")
    if not isinstance(r, dict):
        assert False
    if r.get("eligible") is not True:
        assert False
    try:
        amount = float(r["amount"])
    except (KeyError, TypeError, ValueError):
        assert False
    assert 0.01 <= amount <= 500.0
    # CHECK_END

def test_c05_ordered_sequence():
    trace = load_trace("C05")
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    ok = ordered_subsequence(
        ["authenticate_customer", "get_outage_status"], names, allow_extras=True
    )
    assert ok
    # CHECK_END

def test_c06_forbidden_tools():
    trace = load_trace("C06")
    # CHECK_START
    assert any_forbidden_present(walk_root_tools(trace), ["apply_bill_credit"]) is None
    # CHECK_END

def test_c07_tool_args():
    trace = load_trace("C07")
    # CHECK_START
    tools = walk_root_tools(trace)
    names = tool_names(tools)
    if not ordered_subsequence(
        ["authenticate_customer", "get_line_status"], names, allow_extras=True
    ):
        assert False
    gls = find_tool(tools, "get_line_status")
    assert gls is not None, "get_line_status tool missing"
    lid = gls.get("args", {}).get("line_id")
    assert lid == meta()["line_id"], (
        f"get_line_status.args.line_id expected {meta()['line_id']!r}, got {lid!r}"
    )
    # CHECK_END

def test_c08_tool_result():
    trace = load_trace("C08")
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        assert False
    r = tool.get("result")
    if not isinstance(r, dict) or set(r.keys()) != _C08_REQUIRED_KEYS:
        assert False
    ok = (
        r.get("severity") in ("medium", "high")
        and len(str(r.get("recommended_action", ""))) >= 1
        and len(str(r.get("summary", ""))) >= 10
    )
    assert ok
    # CHECK_END

def test_c09_nested_tools():
    trace = load_trace("C09")
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        assert False
    names = [c.get("name") for c in nested_children(tool)]
    assert names == ["pull_network_events", "score_signal_anomaly"]
    # CHECK_END

def test_c10_unordered_siblings():
    trace = load_trace("C10")
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    assert unordered_set(["heartbeat_ping", "get_line_status"], names, allow_extras=True)
    # CHECK_END

def test_c11_db_state():
    trace = load_trace("C11")
    # CHECK_START
    base = Path(tempfile.mkdtemp(prefix="canon_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        try:
            o.assert_ticket_exists(telco)
            assert True
        except AssertionError:
            assert False
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

def test_c12_multi_turn_memory():
    trace = load_trace("C12")
    # CHECK_START
    turns = trace.get("turns") or []
    if not turns:
        assert False
    last = turns[-1]
    names = tool_names(walk_root_tools(last))
    if not ordered_subsequence(
        ["authenticate_customer", "create_support_ticket"], names, allow_extras=True
    ):
        assert False
    mmeta = meta()
    base = Path(tempfile.mkdtemp(prefix="canon_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=mmeta["line_id"], ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, mmeta["line_id"])
            assert True
        except AssertionError:
            assert False
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

