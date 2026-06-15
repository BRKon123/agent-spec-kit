"""Intentional failing trace variants (one policy violation per C01–C12)."""

from __future__ import annotations

import copy
from typing import Any

from shared.trace_helpers import find_tool, walk_root_tools
from shared.trace_io import load_trace


def _deepcopy_golden(check_id: str) -> dict[str, Any]:
    return copy.deepcopy(load_trace(check_id))


def fail_trace_for(check_id: str) -> dict[str, Any]:
    """Return a trace that should fail the canonical check for ``check_id``."""
    builders = {
        "C01": _fail_c01,
        "C02": _fail_c02,
        "C03": _fail_c03,
        "C04": _fail_c04,
        "C05": _fail_c05,
        "C06": _fail_c06,
        "C07": _fail_c07,
        "C08": _fail_c08,
        "C09": _fail_c09,
        "C10": _fail_c10,
        "C11": _fail_c11,
        "C12": _fail_c12,
    }
    return builders[check_id]()


def _fail_c01() -> dict[str, Any]:
    t = _deepcopy_golden("C01")
    t["output"] = "Your service is active; no billing changes this cycle."
    return t


def _fail_c02() -> dict[str, Any]:
    t = _deepcopy_golden("C02")
    tool = find_tool(walk_root_tools(t), "run_network_diagnostics_specialist")
    if tool and isinstance(tool.get("result"), dict):
        tool["result"]["severity"] = "low"
    return t


def _fail_c03() -> dict[str, Any]:
    t = _deepcopy_golden("C03")
    tool = find_tool(walk_root_tools(t), "run_billing_policy_specialist")
    if tool and isinstance(tool.get("result"), dict):
        tool["result"]["eligible"] = True
        tool["result"].pop("amount", None)
    return t


def _fail_c04() -> dict[str, Any]:
    t = _deepcopy_golden("C04")
    tool = find_tool(walk_root_tools(t), "run_billing_policy_specialist")
    if tool and isinstance(tool.get("result"), dict):
        tool["result"]["amount"] = 9999.0
    return t


def _fail_c05() -> dict[str, Any]:
    t = _deepcopy_golden("C05")
    tools = t.get("tools") or []
    names = [x.get("name") for x in tools if isinstance(x, dict)]
    if "authenticate_customer" in names and "get_outage_status" in names:
        auth = next(x for x in tools if x.get("name") == "authenticate_customer")
        outage = next(x for x in tools if x.get("name") == "get_outage_status")
        t["tools"] = [outage, auth]
    return t


def _fail_c06() -> dict[str, Any]:
    t = _deepcopy_golden("C06")
    t.setdefault("tools", []).append(
        {"name": "apply_bill_credit", "args": {"amount": 10}, "result": "ok"}
    )
    return t


def _fail_c07() -> dict[str, Any]:
    t = _deepcopy_golden("C07")
    tool = find_tool(walk_root_tools(t), "get_line_status")
    if tool and isinstance(tool.get("args"), dict):
        tool["args"]["line_id"] = "LINE-002"
    return t


def _fail_c08() -> dict[str, Any]:
    t = _deepcopy_golden("C08")
    tool = find_tool(walk_root_tools(t), "run_network_diagnostics_specialist")
    if tool and isinstance(tool.get("result"), dict):
        tool["result"]["summary"] = "too short"
    return t


def _fail_c09() -> dict[str, Any]:
    t = _deepcopy_golden("C09")
    tool = find_tool(walk_root_tools(t), "run_network_diagnostics_specialist")
    if tool and tool.get("children"):
        tool["children"] = list(reversed(tool["children"]))
    return t


def _fail_c10() -> dict[str, Any]:
    t = _deepcopy_golden("C10")
    t["tools"] = [x for x in t.get("tools") or [] if x.get("name") == "heartbeat_ping"]
    return t


def _fail_c11() -> dict[str, Any]:
    # Trace unused; marker for store-oracle fail (no ticket inserted in runner).
    return {"_fail_mode": "c11_no_ticket"}


def _fail_c12() -> dict[str, Any]:
    t = _deepcopy_golden("C12")
    turns = t.get("turns") or []
    if turns:
        last = turns[-1]
        last["tools"] = [
            {"name": "authenticate_customer", "args": {}, "result": "ok"},
        ]
    return t
