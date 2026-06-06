"""DeepEval ports — inline BaseMetric, ToolCorrectnessMetric, JsonCorrectnessMetric per check."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from deepeval.metrics import BaseMetric, JsonCorrectnessMetric, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams
from pydantic import BaseModel, ConfigDict, Field

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
    class OutputRubricMetric(BaseMetric):
        def __init__(self, threshold: float = 0.5) -> None:
            self.threshold = threshold
            self.async_mode = False
            self.include_reason = True

        def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            text = str(test_case.actual_output or "").lower()
            topic = "credit" in text or "refund" in text
            money = "$" in text or "dollar" in text
            ok = topic and money
            self.score = 1.0 if ok else 0.0
            self.success = ok
            if not ok:
                missing: list[str] = []
                if not topic:
                    missing.append("credit/refund topic")
                if not money:
                    missing.append("monetary amount ($/dollar)")
                self.reason = f"output rubric failed: missing {', '.join(missing)}"
            return self.score

        async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            if self.error is not None:
                raise AssertionError(self.error)
            return bool(self.success)

    tc = LLMTestCase(
        input="check",
        actual_output=str(trace.get("output", "")),
        tools_called=[
            ToolCall(name=str(t.get("name", "")), input_parameters=dict(t.get("args") or {}))
            for t in trace.get("tools") or []
        ],
    )
    metric = OutputRubricMetric()
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C01", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C02
def eval_c02(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    class NetworkDiagSchema(BaseModel):
        model_config = ConfigDict(extra="forbid")
        severity: Literal["high"]
        recommended_action: Literal["create_ticket"]
        escalation_reason: str = Field(min_length=1)

    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None
    tc = LLMTestCase(
        input="check",
        actual_output=json.dumps(payload) if payload is not None else "",
    )
    metric = JsonCorrectnessMetric(
        expected_schema=NetworkDiagSchema,
        async_mode=False,
        include_reason=True,
    )
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C02", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C03
def eval_c03(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    class ConditionalBillingMetric(BaseMetric):
        def __init__(self, threshold: float = 0.5) -> None:
            self.threshold = threshold
            self.async_mode = False
            self.include_reason = True

        def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            try:
                payload = json.loads(test_case.actual_output or "{}")
            except json.JSONDecodeError as exc:
                self.score = 0.0
                self.success = False
                self.reason = str(exc)
                return self.score
            if not isinstance(payload, dict) or "eligible" not in payload:
                self.score = 0.0
                self.success = False
                self.reason = "run_billing_policy_specialist result missing eligible field"
                return self.score
            if payload.get("eligible"):
                ok = "amount" in payload and float(payload["amount"]) > 0
                if not ok:
                    self.reason = "eligible=True requires positive amount"
            else:
                ok = "amount" not in payload
                if not ok:
                    self.reason = "eligible=False must omit amount"
            self.score = 1.0 if ok else 0.0
            self.success = ok
            return self.score

        async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            if self.error is not None:
                raise AssertionError(self.error)
            return bool(self.success)

    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_billing_policy_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None
    tc = LLMTestCase(
        input="check",
        actual_output=json.dumps(payload) if payload is not None else "",
    )
    metric = ConditionalBillingMetric()
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C03", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C04
def eval_c04(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    class BillingAmountSchema(BaseModel):
        model_config = ConfigDict(extra="forbid")
        eligible: Literal[True]
        amount: float = Field(ge=0.01, le=500.0)

    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_billing_policy_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None
    tc = LLMTestCase(
        input="check",
        actual_output=json.dumps(payload) if payload is not None else "",
    )
    metric = JsonCorrectnessMetric(
        expected_schema=BillingAmountSchema,
        async_mode=False,
        include_reason=True,
    )
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C04", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C05
def eval_c05(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    tc = LLMTestCase(
        input="check",
        actual_output="",
        tools_called=[
            ToolCall(name=str(t.get("name", "")), input_parameters=dict(t.get("args") or {}))
            for t in trace.get("tools") or []
        ],
        expected_tools=[
            ToolCall(name="authenticate_customer", input_parameters={}),
            ToolCall(name="get_outage_status", input_parameters={}),
        ],
    )
    metric = ToolCorrectnessMetric(
        threshold=1.0,
        include_reason=True,
        async_mode=False,
        strict_mode=True,
        should_consider_ordering=True,
        should_exact_match=False,
        evaluation_params=[],
    )
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C05", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C06
def eval_c06(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    class ForbiddenToolMetric(BaseMetric):
        forbidden: str = "apply_bill_credit"

        def __init__(self, threshold: float = 0.5) -> None:
            self.threshold = threshold
            self.async_mode = False
            self.include_reason = True

        def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            called = [tc.name for tc in (test_case.tools_called or [])]
            ok = self.forbidden not in called
            self.score = 1.0 if ok else 0.0
            self.success = ok
            if not ok:
                self.reason = f"forbidden tool {self.forbidden!r} present in {called!r}"
            return self.score

        async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            if self.error is not None:
                raise AssertionError(self.error)
            return bool(self.success)

    tc = LLMTestCase(
        input="check",
        actual_output=str(trace.get("output", "")),
        tools_called=[
            ToolCall(name=str(t.get("name", "")), input_parameters=dict(t.get("args") or {}))
            for t in trace.get("tools") or []
        ],
    )
    metric = ForbiddenToolMetric()
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C06", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C07
def eval_c07(trace: dict[str, Any]) -> dict[str, Any]:
    line_id = meta()["line_id"]
    # CHECK_START
    tc = LLMTestCase(
        input="check",
        actual_output="",
        tools_called=[
            ToolCall(name=str(t.get("name", "")), input_parameters=dict(t.get("args") or {}))
            for t in trace.get("tools") or []
        ],
        expected_tools=[
            ToolCall(name="authenticate_customer", input_parameters={}),
            ToolCall(name="get_line_status", input_parameters={"line_id": line_id}),
        ],
    )
    metric = ToolCorrectnessMetric(
        threshold=1.0,
        include_reason=True,
        async_mode=False,
        strict_mode=True,
        should_consider_ordering=True,
        should_exact_match=False,
        evaluation_params=[ToolCallParams.INPUT_PARAMETERS],
    )
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C07", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C08
def eval_c08(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    class SpecialistSummarySchema(BaseModel):
        model_config = ConfigDict(extra="forbid")
        severity: Literal["medium", "high"]
        recommended_action: str = Field(min_length=1)
        summary: str = Field(min_length=10)

    specialist = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            specialist = t
            break
    payload = specialist.get("result") if specialist else None
    tc = LLMTestCase(
        input="check",
        actual_output=json.dumps(payload) if payload is not None else "",
    )
    metric = JsonCorrectnessMetric(
        expected_schema=SpecialistSummarySchema,
        async_mode=False,
        include_reason=True,
    )
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C08", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C09
def eval_c09(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    class NestedToolsMetric(BaseMetric):
        def __init__(self, threshold: float = 0.5) -> None:
            self.threshold = threshold
            self.async_mode = False
            self.include_reason = True

        def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            try:
                parent = json.loads(test_case.actual_output or "{}")
            except json.JSONDecodeError as exc:
                self.score = 0.0
                self.success = False
                self.reason = str(exc)
                return self.score
            names = [str(c.get("name", "")) for c in (parent.get("children") or [])]
            expected = ["pull_network_events", "score_signal_anomaly"]
            ok = names == expected
            self.score = 1.0 if ok else 0.0
            self.success = ok
            if not ok:
                self.reason = f"nested children expected {expected!r}, got {names!r}"
            return self.score

        async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            if self.error is not None:
                raise AssertionError(self.error)
            return bool(self.success)

    parent = None
    for t in trace.get("tools") or []:
        if t.get("name") == "run_network_diagnostics_specialist":
            parent = t
            break
    tc = LLMTestCase(input="check", actual_output=json.dumps(parent or {}))
    metric = NestedToolsMetric()
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C09", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C10
def eval_c10(trace: dict[str, Any]) -> dict[str, Any]:
    # CHECK_START
    tc = LLMTestCase(
        input="check",
        actual_output="",
        tools_called=[
            ToolCall(name=str(t.get("name", "")), input_parameters=dict(t.get("args") or {}))
            for t in trace.get("tools") or []
        ],
        expected_tools=[
            ToolCall(name="heartbeat_ping", input_parameters={}),
            ToolCall(name="get_line_status", input_parameters={}),
        ],
    )
    metric = ToolCorrectnessMetric(
        threshold=1.0,
        include_reason=True,
        async_mode=False,
        strict_mode=True,
        should_consider_ordering=False,
        should_exact_match=False,
        evaluation_params=[],
    )
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C10", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C11
def eval_c11(trace: dict[str, Any]) -> dict[str, Any]:
    _ = trace
    # CHECK_START
    class DbStateMetric(BaseMetric):
        def __init__(self, threshold: float = 0.5) -> None:
            self.threshold = threshold
            self.async_mode = False
            self.include_reason = True

        def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            base = Path(tempfile.mkdtemp(prefix="de_c11_"))
            try:
                telco = TelcoStore(base / "telco.sqlite")
                apply_seed(telco, "task_T04")
                insert_ticket(telco, line_id=meta()["line_id"])
                try:
                    o.assert_ticket_exists(telco)
                    ok = True
                except AssertionError as exc:
                    ok = False
                    self.reason = str(exc)
            finally:
                shutil.rmtree(base, ignore_errors=True)
            self.score = 1.0 if ok else 0.0
            self.success = ok
            return self.score

        async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            if self.error is not None:
                raise AssertionError(self.error)
            return bool(self.success)

    tc = LLMTestCase(input="check", actual_output="")
    metric = DbStateMetric()
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
    return {"key": "C11", "score": 1 if ok else 0, "message": msg}
    # CHECK_END


# check: C12
def eval_c12(trace: dict[str, Any]) -> dict[str, Any]:
    line_id = meta()["line_id"]
    # CHECK_START
    turns = trace.get("turns") or []
    last_tools = list((turns[-1].get("tools") or []) if turns else [])

    class MultiTurnMemoryMetric(BaseMetric):
        def __init__(self, threshold: float = 0.5) -> None:
            self.threshold = threshold
            self.async_mode = False
            self.include_reason = True

        def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            tc_metric = ToolCorrectnessMetric(
                threshold=1.0,
                include_reason=True,
                async_mode=False,
                strict_mode=True,
                should_consider_ordering=True,
                should_exact_match=False,
                evaluation_params=[],
            )
            tc_metric.measure(test_case)
            tools_ok = bool(tc_metric.is_successful())
            base = Path(tempfile.mkdtemp(prefix="de_c12_"))
            try:
                telco = TelcoStore(base / "telco.sqlite")
                apply_seed(telco, "task_T46")
                insert_ticket(telco, line_id=line_id, ticket_id="INC-9046")
                state_reason = ""
                try:
                    o.assert_ticket_for_line(telco, line_id)
                    state_ok = True
                except AssertionError as exc:
                    state_ok = False
                    state_reason = str(exc)
            finally:
                shutil.rmtree(base, ignore_errors=True)
            ok = tools_ok and state_ok
            self.score = 1.0 if ok else 0.0
            self.success = ok
            if not ok:
                parts: list[str] = []
                if not tools_ok:
                    if tc_metric.reason:
                        parts.append(str(tc_metric.reason).strip())
                    elif tc_metric.error:
                        parts.append(str(tc_metric.error).strip())
                    else:
                        parts.append(f"score={tc_metric.score}")
                if not state_ok:
                    parts.append(state_reason)
                self.reason = "; ".join(parts)
            return self.score

        async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
            return self.measure(test_case)

        def is_successful(self) -> bool:
            if self.error is not None:
                raise AssertionError(self.error)
            return bool(self.success)

    tc = LLMTestCase(
        input="check",
        actual_output="",
        tools_called=[
            ToolCall(name=str(t.get("name", "")), input_parameters=dict(t.get("args") or {}))
            for t in last_tools
        ],
        expected_tools=[
            ToolCall(name="authenticate_customer", input_parameters={}),
            ToolCall(name="create_support_ticket", input_parameters={}),
        ],
    )
    metric = MultiTurnMemoryMetric()
    metric.measure(tc)
    ok = bool(metric.is_successful())
    if metric.reason:
        msg = str(metric.reason).strip()
    elif metric.error:
        msg = str(metric.error).strip()
    elif metric.verbose_logs:
        msg = str(metric.verbose_logs).strip()
    else:
        msg = f"score={metric.score}"
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
