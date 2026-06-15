"""Plain pytest — fully inlined check logic in CHECK regions (LOC benchmark)."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from specimens.messages import meta
from shared.store_sim import insert_ticket
from shared.trace_io import load_trace

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


def test_c01_output_rubric():
    # CHECK_START
    trace = load_trace("C01")
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    assert topic and money
    # CHECK_END


def test_c02_object_shape():
    # CHECK_START
    trace = load_trace("C02")
    tools = list(trace.get("tools") or [])
    tool = None
    for t in tools:
        if t.get("name") == "run_network_diagnostics_specialist":
            tool = t
            break
    if tool is None:
        assert False
    r = tool.get("result")
    if not isinstance(r, dict):
        assert False
    keys = set(r.keys())
    required = {"severity", "recommended_action", "escalation_reason"}
    if keys != required:
        assert False
    ok = (
        r.get("severity") == "high"
        and r.get("recommended_action") == "create_ticket"
        and len(str(r.get("escalation_reason", ""))) >= 1
    )
    assert ok
    # CHECK_END


def test_c03_conditional_object():
    # CHECK_START
    trace = load_trace("C03")
    tools = list(trace.get("tools") or [])
    tool = None
    for t in tools:
        if t.get("name") == "run_billing_policy_specialist":
            tool = t
            break
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
    # CHECK_START
    trace = load_trace("C04")
    tools = list(trace.get("tools") or [])
    tool = None
    for t in tools:
        if t.get("name") == "run_billing_policy_specialist":
            tool = t
            break
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
    # CHECK_START
    trace = load_trace("C05")
    names = [str(t.get("name", "")) for t in trace.get("tools") or []]
    expected = ["authenticate_customer", "get_outage_status"]
    ei = 0
    for name in names:
        if ei < len(expected) and name == expected[ei]:
            ei += 1
    assert ei == len(expected)
    # CHECK_END


def test_c06_forbidden_tools():
    # CHECK_START
    trace = load_trace("C06")
    names = [str(t.get("name", "")) for t in trace.get("tools") or []]
    assert "apply_bill_credit" not in names
    # CHECK_END


def test_c07_tool_args():
    # CHECK_START
    trace = load_trace("C07")
    tools = list(trace.get("tools") or [])
    names = [str(t.get("name", "")) for t in tools]
    expected = ["authenticate_customer", "get_line_status"]
    ei = 0
    for name in names:
        if ei < len(expected) and name == expected[ei]:
            ei += 1
    if ei != len(expected):
        assert False
    gls = None
    for t in tools:
        if t.get("name") == "get_line_status":
            gls = t
            break
    assert gls is not None, "get_line_status tool missing"
    lid = gls.get("args", {}).get("line_id")
    assert lid == meta()["line_id"], (
        f"get_line_status.args.line_id expected {meta()['line_id']!r}, got {lid!r}"
    )
    # CHECK_END


def test_c08_tool_result():
    # CHECK_START
    trace = load_trace("C08")
    tools = list(trace.get("tools") or [])
    tool = None
    for t in tools:
        if t.get("name") == "run_network_diagnostics_specialist":
            tool = t
            break
    if tool is None:
        assert False
    r = tool.get("result")
    required = {"severity", "recommended_action", "summary"}
    if not isinstance(r, dict) or set(r.keys()) != required:
        assert False
    ok = (
        r.get("severity") in ("medium", "high")
        and len(str(r.get("recommended_action", ""))) >= 1
        and len(str(r.get("summary", ""))) >= 10
    )
    assert ok
    # CHECK_END


def test_c09_nested_tools():
    # CHECK_START
    trace = load_trace("C09")
    tools = list(trace.get("tools") or [])
    tool = None
    for t in tools:
        if t.get("name") == "run_network_diagnostics_specialist":
            tool = t
            break
    if tool is None:
        assert False
    names = [c.get("name") for c in (tool.get("children") or [])]
    assert names == ["pull_network_events", "score_signal_anomaly"]
    # CHECK_END


def test_c10_unordered_siblings():
    # CHECK_START
    trace = load_trace("C10")
    names = set(str(t.get("name", "")) for t in trace.get("tools") or [])
    required = {"heartbeat_ping", "get_line_status"}
    assert required <= names
    # CHECK_END


def test_c11_db_state():
    # CHECK_START
    trace = load_trace("C11")
    _ = trace
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
    # CHECK_START
    trace = load_trace("C12")
    turns = trace.get("turns") or []
    if not turns:
        assert False
    last = turns[-1]
    names = [str(t.get("name", "")) for t in (last.get("tools") or [])]
    expected = ["authenticate_customer", "create_support_ticket"]
    ei = 0
    for name in names:
        if ei < len(expected) and name == expected[ei]:
            ei += 1
    if ei != len(expected):
        assert False
    line_id = meta()["line_id"]
    base = Path(tempfile.mkdtemp(prefix="canon_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=line_id, ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, line_id)
            assert True
        except AssertionError:
            assert False
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END
