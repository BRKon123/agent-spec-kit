"""Braintrust-style scorers — inlined check logic in CHECK regions."""

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


_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})
_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})

def _wrap(ok: bool, check_id: str) -> dict[str, Any]:
    return {"key": check_id.lower(), "score": 1 if ok else 0}

def score_c01(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    return _wrap(topic and money, "C01")
    # CHECK_END

def score_c02(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return _wrap(False, "C02")
    r = tool.get("result")
    if not isinstance(r, dict):
        return _wrap(False, "C02")
    keys = set(r.keys())
    if keys != _C02_REQUIRED_KEYS:
        return _wrap(False, "C02")
    ok = (
        r.get("severity") == "high"
        and r.get("recommended_action") == "create_ticket"
        and len(str(r.get("escalation_reason", ""))) >= 1
    )
    return _wrap(ok, "C02")
    # CHECK_END

def score_c03(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        return _wrap(False, "C03")
    r = tool.get("result")
    if not isinstance(r, dict) or "eligible" not in r:
        return _wrap(False, "C03")
    if r.get("eligible"):
        return _wrap("amount" in r and float(r["amount"]) > 0, "C03")
    return _wrap("amount" not in r, "C03")
    # CHECK_END

def score_c04(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_billing_policy_specialist")
    if tool is None:
        return _wrap(False, "C04")
    r = tool.get("result")
    if not isinstance(r, dict):
        return _wrap(False, "C04")
    if r.get("eligible") is not True:
        return _wrap(False, "C04")
    try:
        amount = float(r["amount"])
    except (KeyError, TypeError, ValueError):
        return _wrap(False, "C04")
    return _wrap(0.01 <= amount <= 500.0, "C04")
    # CHECK_END

def score_c05(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    ok = ordered_subsequence(
        ["authenticate_customer", "get_outage_status"], names, allow_extras=True
    )
    return _wrap(ok, "C05")
    # CHECK_END

def score_c06(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    return _wrap(any_forbidden_present(walk_root_tools(trace), ["apply_bill_credit"]) is None, "C06")
    # CHECK_END

def score_c07(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    tools = walk_root_tools(trace)
    names = tool_names(tools)
    if not ordered_subsequence(
        ["authenticate_customer", "get_line_status"], names, allow_extras=True
    ):
        return _wrap(False, "C07")
    gls = find_tool(tools, "get_line_status")
    return _wrap(gls is not None and gls.get("args", {}).get("line_id") == meta()["line_id"], "C07")
    # CHECK_END

def score_c08(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return _wrap(False, "C08")
    r = tool.get("result")
    if not isinstance(r, dict) or set(r.keys()) != _C08_REQUIRED_KEYS:
        return _wrap(False, "C08")
    ok = (
        r.get("severity") in ("medium", "high")
        and len(str(r.get("recommended_action", ""))) >= 1
        and len(str(r.get("summary", ""))) >= 10
    )
    return _wrap(ok, "C08")
    # CHECK_END

def score_c09(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        return _wrap(False, "C09")
    names = [c.get("name") for c in nested_children(tool)]
    return _wrap(names == ["pull_network_events", "score_signal_anomaly"], "C09")
    # CHECK_END

def score_c10(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    return _wrap(unordered_set(["heartbeat_ping", "get_line_status"], names, allow_extras=True), "C10")
    # CHECK_END

def score_c11(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    base = Path(tempfile.mkdtemp(prefix="canon_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        try:
            o.assert_ticket_exists(telco)
            return _wrap(True, "C11")
        except AssertionError:
            return _wrap(False, "C11")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

def score_c12(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:
    trace = output
    # CHECK_START
    turns = trace.get("turns") or []
    if not turns:
        return _wrap(False, "C12")
    last = turns[-1]
    names = tool_names(walk_root_tools(last))
    if not ordered_subsequence(
        ["authenticate_customer", "create_support_ticket"], names, allow_extras=True
    ):
        return _wrap(False, "C12")
    mmeta = meta()
    base = Path(tempfile.mkdtemp(prefix="canon_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=mmeta["line_id"], ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, mmeta["line_id"])
            return _wrap(True, "C12")
        except AssertionError:
            return _wrap(False, "C12")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END

SCORERS: dict[str, Any] = {
    "C01": score_c01,
    "C02": score_c02,
    "C03": score_c03,
    "C04": score_c04,
    "C05": score_c05,
    "C06": score_c06,
    "C07": score_c07,
    "C08": score_c08,
    "C09": score_c09,
    "C10": score_c10,
    "C11": score_c11,
    "C12": score_c12,
}

