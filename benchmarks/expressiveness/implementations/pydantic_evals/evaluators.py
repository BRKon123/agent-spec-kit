"""Pydantic Evals-style evaluators — inlined check logic in CHECK regions."""

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

from collections.abc import Callable

from shared.trace_io import load_trace

_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})
_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})

def eval_c01_output_rubric(check_id: str = "C01") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    return topic and money
    # CHECK_END

def eval_c02_validate_shape(check_id: str = "C02") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return False
    r = tool.get("result")
    if not isinstance(r, dict):
        return False
    keys = set(r.keys())
    if keys != _C02_REQUIRED_KEYS:
        return False
    return (
        r.get("severity") == "high"
        and r.get("recommended_action") == "create_ticket"
        and len(str(r.get("escalation_reason", ""))) >= 1
    )
    # CHECK_END

def eval_c03_conditional(check_id: str = "C03") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        return False
    r = tool.get("result")
    if not isinstance(r, dict) or "eligible" not in r:
        return False
    if r.get("eligible"):
        return "amount" in r and float(r["amount"]) > 0
    return "amount" not in r
    # CHECK_END

def eval_c04_numeric(check_id: str = "C04") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        return False
    r = tool.get("result")
    if not isinstance(r, dict):
        return False
    if r.get("eligible") is not True:
        return False
    try:
        amount = float(r["amount"])
    except (KeyError, TypeError, ValueError):
        return False
    return 0.01 <= amount <= 500.0
    # CHECK_END

def eval_c05_span_sequence(check_id: str = "C05") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    return ordered_subsequence(
        ["authenticate_customer", "get_outage_status"], names, allow_extras=True
    )
    # CHECK_END

def eval_c06_forbid_span(check_id: str = "C06") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    return any_forbidden_present(walk_root_tools(trace), ["apply_bill_credit"]) is None
    # CHECK_END

def eval_c07_tool_args(check_id: str = "C07") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    tools = walk_root_tools(trace)
    names = tool_names(tools)
    if not ordered_subsequence(
        ["authenticate_customer", "get_line_status"], names, allow_extras=True
    ):
        return False
    gls = find_tool(tools, "get_line_status")
    return gls is not None and gls.get("args", {}).get("line_id") == meta()["line_id"]
    # CHECK_END

def eval_c08_tool_result(check_id: str = "C08") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return False
    r = tool.get("result")
    if not isinstance(r, dict) or set(r.keys()) != _C08_REQUIRED_KEYS:
        return False
    return (
        r.get("severity") in ("medium", "high")
        and len(str(r.get("recommended_action", ""))) >= 1
        and len(str(r.get("summary", ""))) >= 10
    )
    # CHECK_END

def eval_c09_nested(check_id: str = "C09") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return False
    names = [c.get("name") for c in nested_children(tool)]
    return names == ["pull_network_events", "score_signal_anomaly"]
    # CHECK_END

def eval_c10_unordered(check_id: str = "C10") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    return unordered_set(["heartbeat_ping", "get_line_status"], names, allow_extras=True)
    # CHECK_END

def eval_c11_db_state(check_id: str = "C11") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    base = Path(tempfile.mkdtemp(prefix="canon_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        try:
            o.assert_ticket_exists(telco)
            return True
        except AssertionError:
            return False
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

def eval_c12_multi_turn(check_id: str = "C12") -> bool:
    trace = load_trace(check_id)
    # CHECK_START
    turns = trace.get("turns") or []
    if not turns:
        return False
    last = turns[-1]
    names = tool_names(walk_root_tools(last))
    if not ordered_subsequence(
        ["authenticate_customer", "create_support_ticket"], names, allow_extras=True
    ):
        return False
    mmeta = meta()
    base = Path(tempfile.mkdtemp(prefix="canon_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=mmeta["line_id"], ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, mmeta["line_id"])
            return True
        except AssertionError:
            return False
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

EVALUATORS: dict[str, Callable[[str], bool]] = {
    "C01": eval_c01_output_rubric,
    "C02": eval_c02_validate_shape,
    "C03": eval_c03_conditional,
    "C04": eval_c04_numeric,
    "C05": eval_c05_span_sequence,
    "C06": eval_c06_forbid_span,
    "C07": eval_c07_tool_args,
    "C08": eval_c08_tool_result,
    "C09": eval_c09_nested,
    "C10": eval_c10_unordered,
    "C11": eval_c11_db_state,
    "C12": eval_c12_multi_turn,
}

