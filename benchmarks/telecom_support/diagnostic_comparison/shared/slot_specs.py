"""Discover trace/output matcher specs from generated fault-detection modules."""

from __future__ import annotations

import importlib
import re
from typing import Any

import agent_spec_kit.match as m


def _module_name(family: str, task: str) -> str:
    return f"tasks.fault_detection.generated.test_{family}_{task}"


def load_generated_module(family: str, task: str) -> Any:
    return importlib.import_module(_module_name(family, task))


def trace_spec_for_slot(family: str, task: str, store: Any) -> list[Any] | None:
    mod = load_generated_module(family, task)
    meta = store.seed_meta
    for name, val in vars(mod).items():
        if name.endswith("_TRACE") and isinstance(val, list):
            return list(val)
    # Inline full-scenario trace patterns (no _TRACE constant)
    src = ""
    try:
        from pathlib import Path

        path = Path(mod.__file__)
        src = path.read_text(encoding="utf-8")
    except OSError:
        return None
    from tasks.specs import trace_oracles as to

    if "to.ticket_on_line" in src and "authenticate_customer" in src:
        return [
            m.tool_call("authenticate_customer"),
            to.ticket_on_line(meta["line_id"]),
        ]
    if "to.order_sim_on_line" in src and "authenticate_customer" in src:
        line = meta.get("line_id") or meta.get("decoy_line_id", "LINE-WRONG")
        return [
            m.tool_call("authenticate_customer"),
            to.order_sim_on_line(str(line)),
        ]
    if "_T17_TRACE" in src or "fault_unsupported_credit" in str(meta):
        return [
            m.tool_call("authenticate_customer"),
            m.tool_call("check_outage"),
            m.tool_call("run_line_diagnostic"),
            m.tool_call("run_billing_policy_specialist"),
        ]
    return None


def forbid_spec_for_slot(family: str, task: str) -> list[Any] | None:
    mod = load_generated_module(family, task)
    for name, val in vars(mod).items():
        if "FORBIDDEN" in name and isinstance(val, list):
            return list(val)
    from tasks.specs import trace_oracles as to

    if hasattr(to, "CREDIT_FORBIDDEN"):
        return list(to.CREDIT_FORBIDDEN)
    if hasattr(to, "ORDER_SIM_FORBIDDEN"):
        return list(to.ORDER_SIM_FORBIDDEN)
    return None


def output_spec_for_slot(family: str, task: str) -> Any | None:
    mod = load_generated_module(family, task)
    for name, val in vars(mod).items():
        if name.endswith("_OUTPUT") or name.endswith("_AFTER_MSG2_OUTPUT"):
            return val
    return None


def parse_forbid_names(expected: str) -> list[str]:
    m = re.search(r"expected no '([^']+)'", expected)
    if m:
        return [m.group(1)]
    return []
