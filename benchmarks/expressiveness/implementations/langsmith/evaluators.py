"""LangSmith-style evaluators — inlined check logic in CHECK regions."""

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

def _score(ok: bool, key: str) -> dict[str, Any]:
    return {"key": key, "score": 1 if ok else 0}

def eval_c01_output_rubric(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    return _score(topic and money, "output_rubric")
    # CHECK_END

def eval_c02_object_shape(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return _score(False, "object_shape")
    r = tool.get("result")
    if not isinstance(r, dict):
        return _score(False, "object_shape")
    keys = set(r.keys())
    if keys != _C02_REQUIRED_KEYS:
        return _score(False, "object_shape")
    ok = (
        r.get("severity") == "high"
        and r.get("recommended_action") == "create_ticket"
        and len(str(r.get("escalation_reason", ""))) >= 1
    )
    return _score(ok, "object_shape")
    # CHECK_END

def eval_c03_conditional_object(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        return _score(False, "conditional_object")
    r = tool.get("result")
    if not isinstance(r, dict) or "eligible" not in r:
        return _score(False, "conditional_object")
    if r.get("eligible"):
        return _score("amount" in r and float(r["amount"]) > 0, "conditional_object")
    return _score("amount" not in r, "conditional_object")
    # CHECK_END

def eval_c04_numeric_regex(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        return _score(False, "numeric_regex")
    r = tool.get("result")
    if not isinstance(r, dict):
        return _score(False, "numeric_regex")
    if r.get("eligible") is not True:
        return _score(False, "numeric_regex")
    try:
        amount = float(r["amount"])
    except (KeyError, TypeError, ValueError):
        return _score(False, "numeric_regex")
    return _score(0.01 <= amount <= 500.0, "numeric_regex")
    # CHECK_END

def eval_c05_ordered_sequence(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    ok = ordered_subsequence(
        ["authenticate_customer", "get_outage_status"], names, allow_extras=True
    )
    return _score(ok, "ordered_sequence")
    # CHECK_END

def eval_c06_forbidden(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    return _score(any_forbidden_present(walk_root_tools(trace), ["apply_bill_credit"]) is None, "forbidden_tools")
    # CHECK_END

def eval_c07_tool_args(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    tools = walk_root_tools(trace)
    names = tool_names(tools)
    if not ordered_subsequence(
        ["authenticate_customer", "get_line_status"], names, allow_extras=True
    ):
        return _score(False, "tool_args")
    gls = find_tool(tools, "get_line_status")
    return _score(gls is not None and gls.get("args", {}).get("line_id") == meta()["line_id"], "tool_args")
    # CHECK_END

def eval_c08_tool_result(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return _score(False, "tool_result")
    r = tool.get("result")
    if not isinstance(r, dict) or set(r.keys()) != _C08_REQUIRED_KEYS:
        return _score(False, "tool_result")
    ok = (
        r.get("severity") in ("medium", "high")
        and len(str(r.get("recommended_action", ""))) >= 1
        and len(str(r.get("summary", ""))) >= 10
    )
    return _score(ok, "tool_result")
    # CHECK_END

def eval_c09_nested(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return _score(False, "nested_tools")
    names = [c.get("name") for c in nested_children(tool)]
    return _score(names == ["pull_network_events", "score_signal_anomaly"], "nested_tools")
    # CHECK_END

def eval_c10_unordered(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    return _score(unordered_set(["heartbeat_ping", "get_line_status"], names, allow_extras=True), "unordered_siblings")
    # CHECK_END

def eval_c11_db_state(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    base = Path(tempfile.mkdtemp(prefix="canon_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        try:
            o.assert_ticket_exists(telco)
            return _score(True, "db_state")
        except AssertionError:
            return _score(False, "db_state")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

def eval_c12_multi_turn_memory(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    turns = trace.get("turns") or []
    if not turns:
        return _score(False, "multi_turn_memory")
    last = turns[-1]
    names = tool_names(walk_root_tools(last))
    if not ordered_subsequence(
        ["authenticate_customer", "create_support_ticket"], names, allow_extras=True
    ):
        return _score(False, "multi_turn_memory")
    mmeta = meta()
    base = Path(tempfile.mkdtemp(prefix="canon_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=mmeta["line_id"], ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, mmeta["line_id"])
            return _score(True, "multi_turn_memory")
        except AssertionError:
            return _score(False, "multi_turn_memory")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

EVALUATORS: dict[str, Any] = {
    "C01": eval_c01_output_rubric,
    "C02": eval_c02_object_shape,
    "C03": eval_c03_conditional_object,
    "C04": eval_c04_numeric_regex,
    "C05": eval_c05_ordered_sequence,
    "C06": eval_c06_forbidden,
    "C07": eval_c07_tool_args,
    "C08": eval_c08_tool_result,
    "C09": eval_c09_nested,
    "C10": eval_c10_unordered,
    "C11": eval_c11_db_state,
    "C12": eval_c12_multi_turn_memory,
}

def run_evaluator(check_id: str, outputs: dict[str, Any] | None = None) -> dict:
    data = outputs if outputs is not None else load_trace(check_id)
    return EVALUATORS[check_id](data)

