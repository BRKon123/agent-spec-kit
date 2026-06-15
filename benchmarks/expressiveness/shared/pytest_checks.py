"""Run expressiveness check bodies against an explicit trace (for fail-sample collection)."""

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

_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})
_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})


def run_check(check_id: str, trace: dict[str, Any]) -> None:
    runners = {
        "C01": _c01,
        "C02": _c02,
        "C03": _c03,
        "C04": _c04,
        "C05": _c05,
        "C06": _c06,
        "C07": _c07,
        "C08": _c08,
        "C09": _c09,
        "C10": _c10,
        "C11": _c11,
        "C12": _c12,
    }
    runners[check_id](trace)


def _c01(trace: dict[str, Any]) -> None:
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    assert topic and money


def _c02(trace: dict[str, Any]) -> None:
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        assert False
    r = tool.get("result")
    if not isinstance(r, dict):
        assert False
    keys = set(r.keys())
    if keys != _C02_REQUIRED_KEYS:
        assert False
    assert (
        r.get("severity") == "high"
        and r.get("recommended_action") == "create_ticket"
        and len(str(r.get("escalation_reason", ""))) >= 1
    )


def _c03(trace: dict[str, Any]) -> None:
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


def _c04(trace: dict[str, Any]) -> None:
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


def _c05(trace: dict[str, Any]) -> None:
    names = tool_names(walk_root_tools(trace))
    assert ordered_subsequence(
        ["authenticate_customer", "get_outage_status"], names, allow_extras=True
    )


def _c06(trace: dict[str, Any]) -> None:
    assert any_forbidden_present(walk_root_tools(trace), ["apply_bill_credit"]) is None


def _c07(trace: dict[str, Any]) -> None:
    tools = walk_root_tools(trace)
    names = tool_names(tools)
    assert ordered_subsequence(
        ["authenticate_customer", "get_line_status"], names, allow_extras=True
    )
    gls = find_tool(tools, "get_line_status")
    assert gls is not None, "get_line_status tool missing"
    lid = gls.get("args", {}).get("line_id")
    assert lid == meta()["line_id"], (
        f"get_line_status.args.line_id expected {meta()['line_id']!r}, got {lid!r}"
    )


def _c08(trace: dict[str, Any]) -> None:
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        assert False
    r = tool.get("result")
    if not isinstance(r, dict) or set(r.keys()) != _C08_REQUIRED_KEYS:
        assert False
    assert (
        r.get("severity") in ("medium", "high")
        and len(str(r.get("recommended_action", ""))) >= 1
        and len(str(r.get("summary", ""))) >= 10
    )


def _c09(trace: dict[str, Any]) -> None:
    tool = find_tool(walk_root_tools(trace), "run_network_diagnostics_specialist")
    if tool is None:
        assert False
    names = [c.get("name") for c in nested_children(tool)]
    assert names == ["pull_network_events", "score_signal_anomaly"]


def _c10(trace: dict[str, Any]) -> None:
    names = tool_names(walk_root_tools(trace))
    assert unordered_set(["heartbeat_ping", "get_line_status"], names, allow_extras=True)


def _c11(trace: dict[str, Any]) -> None:
    base = Path(tempfile.mkdtemp(prefix="canon_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        o.assert_ticket_exists(telco)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _c11_fail_no_ticket(trace: dict[str, Any]) -> None:
    del trace
    base = Path(tempfile.mkdtemp(prefix="canon_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        o.assert_ticket_exists(telco)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _c12(trace: dict[str, Any]) -> None:
    turns = trace.get("turns") or []
    if not turns:
        assert False
    last = turns[-1]
    names = tool_names(walk_root_tools(last))
    assert ordered_subsequence(
        ["authenticate_customer", "create_support_ticket"], names, allow_extras=True
    )
    mmeta = meta()
    base = Path(tempfile.mkdtemp(prefix="canon_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=mmeta["line_id"], ticket_id="INC-9046")
        o.assert_ticket_for_line(telco, mmeta["line_id"])
    finally:
        shutil.rmtree(base, ignore_errors=True)
