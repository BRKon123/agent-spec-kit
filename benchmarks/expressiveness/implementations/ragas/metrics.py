"""Ragas ports — collections ToolCallAccuracy + inline BaseMetric subclasses per check."""

from __future__ import annotations

import json
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

from ragas.messages import AIMessage, HumanMessage, ToolCall, ToolMessage
from ragas.metrics.collections import ToolCallAccuracy
from ragas.metrics.collections.base import BaseMetric as RagasBaseMetric
from ragas.metrics.result import MetricResult

from shared.store_sim import insert_ticket
from shared.trace_io import load_trace
from specimens.messages import meta

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


# check: C01
def eval_c01(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    class OutputRubricMetric(RagasBaseMetric):
        async def ascore(self, response: str) -> MetricResult:
            text = str(response or "").lower()
            topic = "credit" in text or "refund" in text
            money = "$" in text or "dollar" in text
            ok = topic and money
            if ok:
                return MetricResult(value=1.0)
            missing: list[str] = []
            if not topic:
                missing.append("credit/refund topic")
            if not money:
                missing.append("monetary amount ($/dollar)")
            return MetricResult(
                value=0.0,
                reason=f"output rubric failed: missing {', '.join(missing)}",
            )

    metric = OutputRubricMetric(name="C01")
    result = metric.score(response=str(trace.get("output", "")))
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C01", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C02
def eval_c02(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None
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

    class JsonSchemaMetric(RagasBaseMetric):
        async def ascore(self, body: Any) -> MetricResult:
            try:
                jsonschema.validate(instance=body, schema=schema)
                return MetricResult(value=1.0)
            except jsonschema.ValidationError as exc:
                return MetricResult(
                    value=0.0,
                    reason=f"run_network_diagnostics_specialist: {exc.message}",
                )

    metric = JsonSchemaMetric(name="C02")
    result = metric.score(body=payload)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C02", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C03
def eval_c03(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_billing_policy_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None

    class ConditionalBillingMetric(RagasBaseMetric):
        async def ascore(self, body: Any) -> MetricResult:
            if not isinstance(body, dict) or "eligible" not in body:
                return MetricResult(
                    value=0.0,
                    reason="run_billing_policy_specialist result missing eligible field",
                )
            if body.get("eligible"):
                ok = "amount" in body and float(body["amount"]) > 0
                reason = None if ok else "eligible=True requires positive amount"
            else:
                ok = "amount" not in body
                reason = None if ok else "eligible=False must omit amount"
            return MetricResult(value=1.0 if ok else 0.0, reason=reason)

    metric = ConditionalBillingMetric(name="C03")
    result = metric.score(body=payload)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C03", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C04
def eval_c04(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_billing_policy_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None
    schema = {
        "type": "object",
        "required": ["eligible", "amount"],
        "properties": {
            "eligible": {"const": True},
            "amount": {"type": "number", "minimum": 0.01, "maximum": 500},
        },
    }

    class JsonSchemaMetric(RagasBaseMetric):
        async def ascore(self, body: Any) -> MetricResult:
            try:
                jsonschema.validate(instance=body, schema=schema)
                return MetricResult(value=1.0)
            except jsonschema.ValidationError as exc:
                return MetricResult(
                    value=0.0,
                    reason=f"run_billing_policy_specialist: {exc.message}",
                )

    metric = JsonSchemaMetric(name="C04")
    result = metric.score(body=payload)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C04", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C05
def eval_c05(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    names = [str(t.get("name", "")) for t in trace.get("tools") or []]
    expected = ["authenticate_customer", "get_outage_status"]

    class OrderedSubsequenceMetric(RagasBaseMetric):
        async def ascore(self, tool_names: list[str]) -> MetricResult:
            ei = 0
            for name in tool_names:
                if ei < len(expected) and name == expected[ei]:
                    ei += 1
            ok = ei == len(expected)
            if ok:
                return MetricResult(value=1.0)
            return MetricResult(
                value=0.0,
                reason=(
                    f"tool sequence expected {expected!r}, "
                    f"got ordered match {ei}/{len(expected)} in {tool_names!r}"
                ),
            )

    metric = OrderedSubsequenceMetric(name="C05")
    result = metric.score(tool_names=names)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C05", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C06
def eval_c06(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    names = [str(t.get("name", "")) for t in trace.get("tools") or []]
    forbidden = "apply_bill_credit"

    class ForbiddenToolMetric(RagasBaseMetric):
        async def ascore(self, tool_names: list[str]) -> MetricResult:
            ok = forbidden not in tool_names
            if ok:
                return MetricResult(value=1.0)
            return MetricResult(
                value=0.0,
                reason=f"forbidden tool {forbidden!r} present in {tool_names!r}",
            )

    metric = ForbiddenToolMetric(name="C06")
    result = metric.score(tool_names=names)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C06", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C07
def eval_c07(trace: dict[str, Any]) -> dict[str, Any]:
    line_id = meta()["line_id"]
    # CHECK_START
    tools = list(trace.get("tools") or [])
    user_input: list[Any] = [HumanMessage(content="check")]
    if tools:
        user_input.append(
            AIMessage(
                content="",
                tool_calls=[
                    ToolCall(name=str(t.get("name", "")), args=dict(t.get("args") or {}))
                    for t in tools
                ],
            )
        )
        for _ in tools:
            user_input.append(ToolMessage(content="ok"))
    user_input.append(AIMessage(content=str(trace.get("output", ""))))
    reference = [
        ToolCall(name="authenticate_customer", args={}),
        ToolCall(name="get_line_status", args={"line_id": line_id}),
    ]
    metric = ToolCallAccuracy(name="C07", strict_order=True)
    result = metric.score(user_input=user_input, reference_tool_calls=reference)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C07", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C08
def eval_c08(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None
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

    class JsonSchemaMetric(RagasBaseMetric):
        async def ascore(self, body: Any) -> MetricResult:
            try:
                jsonschema.validate(instance=body, schema=schema)
                return MetricResult(value=1.0)
            except jsonschema.ValidationError as exc:
                return MetricResult(
                    value=0.0,
                    reason=f"run_network_diagnostics_specialist: {exc.message}",
                )

    metric = JsonSchemaMetric(name="C08")
    result = metric.score(body=payload)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C08", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C09
def eval_c09(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    parent = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            parent = t
            break

    class NestedToolsMetric(RagasBaseMetric):
        async def ascore(self, node: dict[str, Any] | None) -> MetricResult:
            if node is None:
                return MetricResult(value=0.0, reason="missing run_network_diagnostics_specialist")
            child_names = [str(c.get("name", "")) for c in (node.get("children") or [])]
            expected = ["pull_network_events", "score_signal_anomaly"]
            ok = child_names == expected
            if ok:
                return MetricResult(value=1.0)
            return MetricResult(
                value=0.0,
                reason=f"nested children expected {expected!r}, got {child_names!r}",
            )

    metric = NestedToolsMetric(name="C09")
    result = metric.score(node=parent)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C09", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C10
def eval_c10(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    names = [str(t.get("name", "")) for t in trace.get("tools") or []]
    required = {"heartbeat_ping", "get_line_status"}

    class UnorderedToolsMetric(RagasBaseMetric):
        async def ascore(self, tool_names: list[str]) -> MetricResult:
            present = set(tool_names)
            ok = required <= present
            if ok:
                return MetricResult(value=1.0)
            missing = sorted(required - present)
            return MetricResult(
                value=0.0,
                reason=f"missing required tools {missing!r} in {tool_names!r}",
            )

    metric = UnorderedToolsMetric(name="C10")
    result = metric.score(tool_names=names)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C10", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C11
def eval_c11(trace: dict[str, Any]) -> dict[str, Any]:
    _ = trace
    # CHECK_START
    class DbStateMetric(RagasBaseMetric):
        async def ascore(self) -> MetricResult:
            base = Path(tempfile.mkdtemp(prefix="rg_c11_"))
            try:
                telco = TelcoStore(base / "telco.sqlite")
                apply_seed(telco, "task_T04")
                insert_ticket(telco, line_id=meta()["line_id"])
                try:
                    o.assert_ticket_exists(telco)
                    return MetricResult(value=1.0)
                except AssertionError as exc:
                    return MetricResult(value=0.0, reason=str(exc))
            finally:
                shutil.rmtree(base, ignore_errors=True)

    metric = DbStateMetric(name="C11")
    result = metric.score()
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C11", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C12
def eval_c12(trace: dict[str, Any]) -> dict[str, Any]:
    line_id = meta()["line_id"]
    # CHECK_START
    turns = trace.get("turns") or []
    tools = list((turns[-1].get("tools") or []) if turns else [])
    names = [str(t.get("name", "")) for t in tools]
    expected = ["authenticate_customer", "create_support_ticket"]
    ei = 0
    for name in names:
        if ei < len(expected) and name == expected[ei]:
            ei += 1
    tools_ok = ei == len(expected)

    class MultiTurnMemoryMetric(RagasBaseMetric):
        async def ascore(self, state_ok: bool, state_reason: str) -> MetricResult:
            ok = tools_ok and state_ok
            if ok:
                return MetricResult(value=1.0)
            parts: list[str] = []
            if not tools_ok:
                parts.append(
                    f"tool sequence expected {expected!r}, "
                    f"got ordered match {ei}/{len(expected)} in {names!r}"
                )
            if not state_ok:
                parts.append(state_reason)
            return MetricResult(value=0.0, reason="; ".join(parts))

    base = Path(tempfile.mkdtemp(prefix="rg_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=line_id, ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, line_id)
            state_ok = True
            state_reason = ""
        except AssertionError as exc:
            state_ok = False
            state_reason = str(exc)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    metric = MultiTurnMemoryMetric(name="C12")
    result = metric.score(state_ok=state_ok, state_reason=state_reason)
    ok = float(result.value) >= 1.0
    msg = (result.reason or str(result.value)).strip()
    return {"key": "C12", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


EVALUATORS: dict[str, Any] = {
    "C01": eval_c01,
    "C02": eval_c02,
    "C03": eval_c03,
    "C04": eval_c04,
    "C05": eval_c05,
    "C06": eval_c06,
    "C07": eval_c07,
    "C08": eval_c08,
    "C09": eval_c09,
    "C10": eval_c10,
    "C11": eval_c11,
    "C12": eval_c12,
}


def run_evaluator(check_id: str, trace: dict[str, Any] | None = None) -> dict[str, Any]:
    data = trace if trace is not None else load_trace(check_id)
    return EVALUATORS[check_id](data)


def fail_message_for_trace(check_id: str, trace: dict[str, Any]) -> str:
    result = run_evaluator(check_id, trace)
    if result.get("score") == 1:
        return "unexpected pass"
    msg = result.get("message") or str(result)
    return msg if isinstance(msg, str) else str(msg)


CHECK_IDS = [f"C{i:02d}" for i in range(1, 13)]
