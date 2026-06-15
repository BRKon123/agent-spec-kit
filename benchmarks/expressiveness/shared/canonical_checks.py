"""
Authoritative oracle semantics for expressiveness specimens C01–C12.

Reference oracles for uniformity tests. Framework ports inline the same logic
inside CHECK_START/END (regenerate via scripts/materialize_inline_checks.py).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

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

_TELECOM = Path(__file__).resolve().parents[1].parent / "telecom_support"
import sys

if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402

# --- C01: deterministic output rubric proxy (same across all frameworks) ---


def check_c01_output_rubric(trace: dict[str, Any]) -> bool:
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    return topic and money


# --- C02: structured object on specialist result ---

_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})


def check_c02_object_shape(trace: dict[str, Any]) -> bool:
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


# --- C03: conditional billing result ---


def check_c03_conditional_object(trace: dict[str, Any]) -> bool:
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        return False
    r = tool.get("result")
    if not isinstance(r, dict) or "eligible" not in r:
        return False
    if r.get("eligible"):
        return "amount" in r and float(r["amount"]) > 0
    return "amount" not in r


# --- C04: numeric range on billing amount (eligible true) ---


def check_c04_numeric_regex(trace: dict[str, Any]) -> bool:
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


# --- C05: ordered tool subsequence ---


def check_c05_ordered_sequence(trace: dict[str, Any]) -> bool:
    names = tool_names(walk_root_tools(trace))
    return ordered_subsequence(
        ["authenticate_customer", "get_outage_status"], names, allow_extras=True
    )


# --- C06: forbidden root tool ---


def check_c06_forbidden_tools(trace: dict[str, Any]) -> bool:
    return any_forbidden_present(walk_root_tools(trace), ["apply_bill_credit"]) is None


# --- C07: ordered auth then get_line_status with line_id arg ---


def check_c07_tool_args(trace: dict[str, Any]) -> bool:
    tools = walk_root_tools(trace)
    names = tool_names(tools)
    if not ordered_subsequence(
        ["authenticate_customer", "get_line_status"], names, allow_extras=True
    ):
        return False
    gls = find_tool(tools, "get_line_status")
    return gls is not None and gls.get("args", {}).get("line_id") == meta()["line_id"]


# --- C08: specialist result shape ---

_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})


def check_c08_tool_result(trace: dict[str, Any]) -> bool:
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


# --- C09: nested children order ---


def check_c09_nested_tools(trace: dict[str, Any]) -> bool:
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return False
    names = [c.get("name") for c in nested_children(tool)]
    return names == ["pull_network_events", "score_signal_anomaly"]


# --- C10: unordered siblings ---


def check_c10_unordered_siblings(trace: dict[str, Any]) -> bool:
    names = tool_names(walk_root_tools(trace))
    return unordered_set(["heartbeat_ping", "get_line_status"], names, allow_extras=True)


# --- C11: ticket row exists (state only; trace simulates post-hoc) ---


def check_c11_db_state(_trace: dict[str, Any]) -> bool:
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


# --- C12: last-turn tools + ticket on corrected line ---


def check_c12_multi_turn_memory(trace: dict[str, Any]) -> bool:
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


CHECK_BY_ID: dict[str, Any] = {
    "C01": check_c01_output_rubric,
    "C02": check_c02_object_shape,
    "C03": check_c03_conditional_object,
    "C04": check_c04_numeric_regex,
    "C05": check_c05_ordered_sequence,
    "C06": check_c06_forbidden_tools,
    "C07": check_c07_tool_args,
    "C08": check_c08_tool_result,
    "C09": check_c09_nested_tools,
    "C10": check_c10_unordered_siblings,
    "C11": check_c11_db_state,
    "C12": check_c12_multi_turn_memory,
}
