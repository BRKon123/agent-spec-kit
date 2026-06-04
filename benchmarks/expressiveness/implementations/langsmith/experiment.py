"""LangSmith ports — code evaluators, agentevals trajectories, jsonschema (no Pydantic)."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from agentevals.trajectory.match import create_trajectory_match_evaluator

from implementations.langsmith.trajectory_bridge import reference_messages_for_tools, trace_to_messages
from specimens.messages import meta
from shared.store_sim import insert_ticket
from shared.trace_io import load_trace

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


def _score(ok: bool, key: str) -> dict[str, Any]:
    return {"key": key, "score": 1 if ok else 0}


def _tool(trace: dict[str, Any], name: str) -> dict[str, Any] | None:
    for t in trace.get("tools") or []:
        if t.get("name") == name:
            return t
    return None


# check: C01
def eval_c01_output_rubric(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    text = str(trace.get("output", "")).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    return _score(topic and money, "output_rubric")
    # CHECK_END


# check: C02
def eval_c02_object_shape(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    specialist = _tool(trace, "run_network_diagnostics_specialist")
    if specialist is None:
        return _score(False, "object_shape")
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
        jsonschema.validate(instance=specialist.get("result"), schema=schema)
        return _score(True, "object_shape")
    except jsonschema.ValidationError:
        return _score(False, "object_shape")
    # CHECK_END


# check: C03
def eval_c03_conditional_object(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    specialist = _tool(trace, "run_billing_policy_specialist")
    if specialist is None:
        return _score(False, "conditional_object")
    r = specialist.get("result")
    if not isinstance(r, dict) or "eligible" not in r:
        return _score(False, "conditional_object")
    if r.get("eligible"):
        ok = "amount" in r and float(r["amount"]) > 0
    else:
        ok = "amount" not in r
    return _score(ok, "conditional_object")
    # CHECK_END


# check: C04
def eval_c04_numeric_regex(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    specialist = _tool(trace, "run_billing_policy_specialist")
    if specialist is None:
        return _score(False, "numeric_regex")
    schema = {
        "type": "object",
        "required": ["eligible", "amount"],
        "properties": {
            "eligible": {"const": True},
            "amount": {"type": "number", "minimum": 0.01, "maximum": 500},
        },
    }
    try:
        jsonschema.validate(instance=specialist.get("result"), schema=schema)
        return _score(True, "numeric_regex")
    except jsonschema.ValidationError:
        return _score(False, "numeric_regex")
    # CHECK_END


# check: C05
def eval_c05_ordered_sequence(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    act = trace_to_messages(trace)
    ref = reference_messages_for_tools(
        [
            {"name": "authenticate_customer", "args": {}},
            {"name": "get_outage_status", "args": {}},
        ]
    )
    has_required = create_trajectory_match_evaluator(
        trajectory_match_mode="superset", tool_args_match_mode="ignore"
    )(outputs=act, reference_outputs=ref)["score"]
    names = [str(t.get("name", "")) for t in trace.get("tools") or []]
    exp = ["authenticate_customer", "get_outage_status"]
    ei = 0
    for name in names:
        if ei < len(exp) and name == exp[ei]:
            ei += 1
    return _score(bool(has_required) and ei == len(exp), "ordered_sequence")
    # CHECK_END


# check: C06
def eval_c06_forbidden(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    names = {str(t.get("name", "")) for t in trace.get("tools") or []}
    return _score("apply_bill_credit" not in names, "forbidden_tools")
    # CHECK_END


# check: C07
def eval_c07_tool_args(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    line_id = meta()["line_id"]
    # CHECK_START
    act = trace_to_messages(trace)
    ref = reference_messages_for_tools(
        [
            {"name": "authenticate_customer", "args": {}},
            {"name": "get_line_status", "args": {"line_id": line_id}},
        ]
    )
    match = create_trajectory_match_evaluator(
        trajectory_match_mode="strict",
        tool_args_match_overrides={"get_line_status": lambda a, b: a.get("line_id") == b.get("line_id")},
    )(outputs=act, reference_outputs=ref)
    return _score(bool(match["score"]), "tool_args")
    # CHECK_END


# check: C08
def eval_c08_tool_result(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    specialist = _tool(trace, "run_network_diagnostics_specialist")
    if specialist is None:
        return _score(False, "tool_result")
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
        jsonschema.validate(instance=specialist.get("result"), schema=schema)
        return _score(True, "tool_result")
    except jsonschema.ValidationError:
        return _score(False, "tool_result")
    # CHECK_END


# check: C09
def eval_c09_nested(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    parent = _tool(trace, "run_network_diagnostics_specialist")
    if parent is None:
        return _score(False, "nested_tools")
    names = [str(c.get("name", "")) for c in parent.get("children") or []]
    return _score(names == ["pull_network_events", "score_signal_anomaly"], "nested_tools")
    # CHECK_END


# check: C10
def eval_c10_unordered(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    # CHECK_START
    act = trace_to_messages(trace)
    ref = reference_messages_for_tools(
        [
            {"name": "heartbeat_ping", "args": {}},
            {"name": "get_line_status", "args": {}},
        ]
    )
    match = create_trajectory_match_evaluator(
        trajectory_match_mode="superset", tool_args_match_mode="ignore"
    )(outputs=act, reference_outputs=ref)
    return _score(bool(match["score"]), "unordered_siblings")
    # CHECK_END


# check: C11
def eval_c11_db_state(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    _ = outputs
    # CHECK_START
    base = Path(tempfile.mkdtemp(prefix="ls_c11_"))
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


# check: C12
def eval_c12_multi_turn_memory(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:
    trace = outputs
    line_id = meta()["line_id"]
    # CHECK_START
    act = trace_to_messages(trace, turn="last")
    ref = reference_messages_for_tools(
        [
            {"name": "authenticate_customer", "args": {}},
            {"name": "create_support_ticket", "args": {"line_id": line_id}},
        ]
    )
    tools_ok = create_trajectory_match_evaluator(
        trajectory_match_mode="superset", tool_args_match_mode="ignore"
    )(outputs=act, reference_outputs=ref)["score"]
    base = Path(tempfile.mkdtemp(prefix="ls_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=line_id, ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, line_id)
            state_ok = True
        except AssertionError:
            state_ok = False
        return _score(bool(tools_ok) and state_ok, "multi_turn_memory")
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

CHECK_IDS = [f"C{i:02d}" for i in range(1, 13)]

# Native LangSmith layout: code evaluators attached per example in evaluate() (harness runs one per specimen).
EXPERIMENT_EVALUATORS = [EVALUATORS[cid] for cid in CHECK_IDS]

