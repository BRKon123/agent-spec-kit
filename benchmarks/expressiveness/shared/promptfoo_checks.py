"""Run Promptfoo-equivalent asserts on a trace (fail-sample harness; mirrors promptfooconfig.yaml)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import jsonschema
from agentevals.trajectory.match import create_trajectory_match_evaluator

from implementations.langsmith.trajectory_bridge import reference_messages_for_tools, trace_to_messages
from implementations.promptfoo.trace_spans import frozen_trace_to_promptfoo_trace
from specimens.messages import meta
from shared.store_sim import insert_ticket

_TELECOM = Path(__file__).resolve().parents[1].parent / "telecom_support"
import sys

if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


def _tool_result(trace: dict[str, Any], name: str) -> Any:
    for t in trace.get("tools") or []:
        if t.get("name") == name:
            return t.get("result")
    return None


def _ordered_trajectory_fail(trace: dict[str, Any], steps: list[str], *, turn: str | None = None) -> str:
    act = trace_to_messages(trace, turn=turn)
    ref = reference_messages_for_tools([{"name": s, "args": {}} for s in steps])
    r = create_trajectory_match_evaluator(
        trajectory_match_mode="superset", tool_args_match_mode="ignore"
    )(outputs=act, reference_outputs=ref)
    if r.get("score") == 1:
        tools = (trace.get("turns") or [])[-1].get("tools") if turn == "last" else trace.get("tools")
        names = [str(t.get("name", "")) for t in tools or []]
        ei = 0
        for name in names:
            if ei < len(steps) and name == steps[ei]:
                ei += 1
        if ei == len(steps):
            return "unexpected pass"
    return f"trajectory:tool-sequence in_order failed for steps {steps!r} (agentevals score={r.get('score')})"


def _tool_used(trace: dict[str, Any], tool_name: str) -> bool:
    pf = frozen_trace_to_promptfoo_trace(trace, "C10")
    return any(
        s.get("attributes", {}).get("tool.name") == tool_name for s in pf.get("spans") or []
    )


def run_check(check_id: str, trace: dict[str, Any]) -> tuple[bool, str]:
    """Return (passed, message). Message is native-style diagnostic text on failure."""
    out = json.dumps(trace)

    if check_id == "C01":
        text = str(trace.get("output", "")).lower()
        if ("credit" in text or "refund" in text) and ("$" in text or "dollar" in text):
            return True, ""
        return False, "icontains-any: output missing credit/refund or $/dollar"

    if check_id == "C02":
        result = _tool_result(trace, "run_network_diagnostics_specialist")
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["severity", "recommended_action", "escalation_reason"],
            "properties": {
                "severity": {"const": "high"},
                "recommended_action": {"const": "create_ticket"},
                "escalation_reason": {"type": "string", "minLength": 1},
            },
        }
        try:
            jsonschema.validate(instance=result, schema=schema)
            return True, ""
        except jsonschema.ValidationError as exc:
            return False, f"is-json: {exc.message}"

    if check_id == "C03":
        t = next((x for x in trace.get("tools") or [] if x.get("name") == "run_billing_policy_specialist"), None)
        if not t or not isinstance(t.get("result"), dict):
            return False, "javascript: missing run_billing_policy_specialist result"
        r = t["result"]
        if "eligible" not in r:
            return False, "javascript: eligible missing"
        if r.get("eligible"):
            if not (isinstance(r.get("amount"), (int, float)) and r["amount"] > 0):
                return False, "javascript: eligible=True requires amount > 0"
        elif "amount" in r:
            return False, "javascript: ineligible must omit amount"
        return True, ""

    if check_id == "C04":
        result = _tool_result(trace, "run_billing_policy_specialist")
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["eligible", "amount"],
            "properties": {
                "eligible": {"const": True},
                "amount": {"type": "number", "minimum": 0.01, "maximum": 500},
            },
        }
        try:
            jsonschema.validate(instance=result, schema=schema)
            return True, ""
        except jsonschema.ValidationError as exc:
            return False, f"is-json: {exc.message}"

    if check_id == "C05":
        msg = _ordered_trajectory_fail(
            trace, ["authenticate_customer", "get_outage_status"]
        )
        return msg == "unexpected pass", msg

    if check_id == "C06":
        if _tool_used(trace, "apply_bill_credit"):
            return False, "not-trajectory:tool-used: forbidden tool apply_bill_credit present"
        return True, ""

    if check_id == "C07":
        msg = _ordered_trajectory_fail(trace, ["authenticate_customer", "get_line_status"])
        if msg != "unexpected pass":
            return False, msg
        from shared.trace_helpers import find_tool, walk_root_tools

        gls = find_tool(walk_root_tools(trace), "get_line_status")
        if gls is None:
            return False, "trajectory:tool-args-match: get_line_status missing"
        lid = gls.get("args", {}).get("line_id")
        expected = meta()["line_id"]
        if lid != expected:
            return False, (
                f"trajectory:tool-args-match get_line_status.line_id "
                f"expected {expected!r}, got {lid!r}"
            )
        return True, ""

    if check_id == "C08":
        result = _tool_result(trace, "run_network_diagnostics_specialist")
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["severity", "recommended_action", "summary"],
            "properties": {
                "severity": {"enum": ["medium", "high"]},
                "recommended_action": {"type": "string", "minLength": 1},
                "summary": {"type": "string", "minLength": 10},
            },
        }
        try:
            jsonschema.validate(instance=result, schema=schema)
            return True, ""
        except jsonschema.ValidationError as exc:
            return False, f"is-json: {exc.message}"

    if check_id == "C09":
        parent = next(
            (x for x in trace.get("tools") or [] if x.get("name") == "run_network_diagnostics_specialist"),
            None,
        )
        if not parent:
            return False, "javascript: missing parent tool"
        names = [c.get("name") for c in parent.get("children") or []]
        if names == ["pull_network_events", "score_signal_anomaly"]:
            return True, ""
        return False, (
            "javascript: nested children expected "
            "['pull_network_events', 'score_signal_anomaly'], "
            f"got {names!r}"
        )

    if check_id == "C10":
        missing = [
            t
            for t in ("heartbeat_ping", "get_line_status")
            if not _tool_used(trace, t)
        ]
        if missing:
            return False, f"trajectory:tool-used: missing tools {missing!r}"
        return True, ""

    if check_id == "C11":
        base = Path(tempfile.mkdtemp(prefix="pf_c11_"))
        try:
            telco = TelcoStore(base / "telco.sqlite")
            apply_seed(telco, "task_T04")
            try:
                o.assert_ticket_exists(telco)
                return False, "unexpected pass"
            except AssertionError as exc:
                return False, str(exc)
        finally:
            shutil.rmtree(base, ignore_errors=True)

    if check_id == "C12":
        msg = _ordered_trajectory_fail(
            trace,
            ["authenticate_customer", "create_support_ticket"],
            turn="last",
        )
        if msg != "unexpected pass":
            return False, msg
        from implementations.promptfoo.assert_c12 import get_assert

        if get_assert(out, {}) is True:
            return True, ""
        line_id = meta()["line_id"]
        base = Path(tempfile.mkdtemp(prefix="pf_c12_"))
        try:
            telco = TelcoStore(base / "telco.sqlite")
            apply_seed(telco, "task_T46")
            try:
                o.assert_ticket_for_line(telco, line_id)
                return False, "unexpected pass"
            except AssertionError as exc:
                return False, f"python assert_c12: {exc}"
        finally:
            shutil.rmtree(base, ignore_errors=True)

    return False, f"unknown check_id {check_id!r}"
