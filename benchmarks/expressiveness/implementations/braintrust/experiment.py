"""Braintrust ports — inlined Score scorers over output + metadata.tool_calls."""

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

from braintrust.score import Score

from specimens.messages import meta
from shared.store_sim import insert_ticket

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


# check: C01
def score_c01(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    metadata = kwargs.get("metadata") or {}
    # CHECK_START
    text = str(metadata.get("output_text", output.get("output", ""))).lower()
    topic = "credit" in text or "refund" in text
    money = "$" in text or "dollar" in text
    ok = topic and money
    score = Score(name="C01", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C02
def score_c02(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    trace = output
    # CHECK_START
    result = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            result = t.get("result")
            break
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
        ok = True
    except jsonschema.ValidationError:
        ok = False
    score = Score(name="C02", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C03
def score_c03(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    trace = output
    # CHECK_START
    result = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_billing_policy_specialist":
            result = t.get("result")
            break
    if not isinstance(result, dict) or "eligible" not in result:
        ok = False
    elif result.get("eligible"):
        ok = "amount" in result and float(result["amount"]) > 0
    else:
        ok = "amount" not in result
    score = Score(name="C03", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C04
def score_c04(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    trace = output
    # CHECK_START
    result = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_billing_policy_specialist":
            result = t.get("result")
            break
    schema = {
        "type": "object",
        "required": ["eligible", "amount"],
        "properties": {
            "eligible": {"const": True},
            "amount": {"type": "number", "minimum": 0.01, "maximum": 500},
        },
    }
    try:
        jsonschema.validate(instance=result, schema=schema)
        ok = True
    except jsonschema.ValidationError:
        ok = False
    score = Score(name="C04", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C05
def score_c05(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    metadata = kwargs.get("metadata") or {}
    # CHECK_START
    calls = list(metadata.get("tool_calls") or [])
    names = [str(c.get("name", "")) for c in calls]
    exp = ["authenticate_customer", "get_outage_status"]
    ei = 0
    for name in names:
        if ei < len(exp) and name == exp[ei]:
            ei += 1
    ok = ei == len(exp)
    score = Score(name="C05", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C06
def score_c06(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    metadata = kwargs.get("metadata") or {}
    # CHECK_START
    calls = list(metadata.get("tool_calls") or [])
    names = {str(c.get("name", "")) for c in calls}
    ok = "apply_bill_credit" not in names
    score = Score(name="C06", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C07
def score_c07(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    metadata = kwargs.get("metadata") or {}
    line_id = meta()["line_id"]
    # CHECK_START
    calls = list(metadata.get("tool_calls") or [])
    names = [str(c.get("name", "")) for c in calls]
    exp = ["authenticate_customer", "get_line_status"]
    ei = 0
    for name in names:
        if ei < len(exp) and name == exp[ei]:
            ei += 1
    if ei != len(exp):
        score = Score(name="C07", score=0.0)
        return {"key": score.name, "score": 0 if score.score is None else score.score}
    gls = None
    for c in calls:
        if c.get("name") == "get_line_status":
            gls = c
            break
    ok = gls is not None and gls.get("args", {}).get("line_id") == line_id
    score = Score(name="C07", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C08
def score_c08(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    trace = output
    # CHECK_START
    result = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            result = t.get("result")
            break
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
        ok = True
    except jsonschema.ValidationError:
        ok = False
    score = Score(name="C08", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C09
def score_c09(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    trace = output
    # CHECK_START
    parent = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            parent = t
            break
    if parent is None:
        score = Score(name="C09", score=0.0)
        return {"key": score.name, "score": 0 if score.score is None else score.score}
    names = [str(c.get("name", "")) for c in parent.get("children") or []]
    ok = names == ["pull_network_events", "score_signal_anomaly"]
    score = Score(name="C09", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C10
def score_c10(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    metadata = kwargs.get("metadata") or {}
    # CHECK_START
    calls = list(metadata.get("tool_calls") or [])
    names = {str(c.get("name", "")) for c in calls}
    required = {"heartbeat_ping", "get_line_status"}
    ok = required <= names
    score = Score(name="C10", score=1.0 if ok else 0.0)
    return {"key": score.name, "score": 0 if score.score is None else score.score}
    # CHECK_END


# check: C11
def score_c11(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    # CHECK_START
    base = Path(tempfile.mkdtemp(prefix="bt_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        try:
            o.assert_ticket_exists(telco)
            ok = True
        except AssertionError:
            ok = False
        score = Score(name="C11", score=1.0 if ok else 0.0)
        return {"key": score.name, "score": 0 if score.score is None else score.score}
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END


# check: C12
def score_c12(
    input: dict[str, Any], output: dict[str, Any], expected: dict[str, Any] | None = None, **kwargs: Any
) -> dict:
    metadata = kwargs.get("metadata") or {}
    line_id = meta()["line_id"]
    # CHECK_START
    calls = list(metadata.get("tool_calls") or [])
    names = [str(c.get("name", "")) for c in calls]
    exp = ["authenticate_customer", "create_support_ticket"]
    ei = 0
    for name in names:
        if ei < len(exp) and name == exp[ei]:
            ei += 1
    if ei != len(exp):
        score = Score(name="C12", score=0.0)
        return {"key": score.name, "score": 0 if score.score is None else score.score}
    base = Path(tempfile.mkdtemp(prefix="bt_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=line_id, ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, line_id)
            state_ok = True
        except AssertionError:
            state_ok = False
        score = Score(name="C12", score=1.0 if state_ok else 0.0)
        return {"key": score.name, "score": 0 if score.score is None else score.score}
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


def metadata_for_trace(trace: dict[str, Any], check_id: str) -> dict[str, Any]:
    """Harness: Braintrust hooks.metadata-style payload from a frozen trace."""
    if check_id == "C12":
        turns = trace.get("turns") or []
        tools = (turns[-1].get("tools") or []) if turns else []
    else:
        tools = trace.get("tools") or []
    return {
        "tool_calls": [{"name": t.get("name"), "args": t.get("args") or {}} for t in tools],
        "output_text": str(trace.get("output", "")),
    }


CHECK_IDS = [f"C{i:02d}" for i in range(1, 13)]

EXPRESSIVENESS_SCORERS = [SCORERS[cid] for cid in CHECK_IDS]
