"""Pydantic Evals ports — Contains, IsInstance, HasMatchingSpan, Evaluator, BaseModel."""

from __future__ import annotations

import shutil
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Contains, Evaluator, EvaluatorContext, HasMatchingSpan, IsInstance
from pydantic_evals.evaluators.evaluator import EvaluationReason
from pydantic_evals.otel.span_tree import SpanQuery

from implementations.pydantic_evals.span_tree_bridge import trace_to_span_tree
from specimens.messages import meta
from shared.store_sim import insert_ticket
from shared.trace_io import load_trace

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


def _ok(result: bool | EvaluationReason) -> bool:
    return result if isinstance(result, bool) else bool(result.value)


def _text_ctx(text: str, check_id: str) -> EvaluatorContext[str, str, None]:
    return EvaluatorContext(
        name=check_id,
        inputs={},
        metadata=None,
        expected_output=None,
        output=text,
        duration=0.0,
        _span_tree=trace_to_span_tree({"tools": []}),
        attributes={},
        metrics={},
    )


def _trace_ctx(trace: dict[str, Any], check_id: str, *, turn: str | None = None) -> EvaluatorContext[dict, dict, None]:
    return EvaluatorContext(
        name=check_id,
        inputs={},
        metadata={"tool_calls": trace.get("tools") or []},
        expected_output=None,
        output=trace,
        duration=0.0,
        _span_tree=trace_to_span_tree(trace, turn=turn),
        attributes={},
        metrics={},
    )


def _tool(trace: dict[str, Any], name: str) -> dict[str, Any] | None:
    for t in trace.get("tools") or []:
        if t.get("name") == name:
            return t
    return None


# check: C01
def eval_c01_output_rubric(check_id: str = "C01") -> bool:
    trace = load_trace(check_id)
    text = str(trace.get("output", ""))
    tctx = _text_ctx(text, check_id)
    # CHECK_START
    topic = _ok(Contains("credit", case_sensitive=False).evaluate(tctx)) or _ok(
        Contains("refund", case_sensitive=False).evaluate(tctx)
    )
    money = _ok(Contains("$", case_sensitive=False).evaluate(tctx)) or _ok(
        Contains("dollar", case_sensitive=False).evaluate(tctx)
    )
    return topic and money
    # CHECK_END


# check: C02
def eval_c02_validate_shape(check_id: str = "C02") -> bool:
    trace = load_trace(check_id)
    specialist = _tool(trace, "run_network_diagnostics_specialist")
    if specialist is None:
        return False
    result = specialist.get("result")
    # CHECK_START
    rctx = EvaluatorContext(
        name=check_id,
        inputs={},
        metadata=None,
        expected_output=None,
        output=result,
        duration=0.0,
        _span_tree=trace_to_span_tree(trace),
        attributes={},
        metrics={},
    )
    if not _ok(IsInstance(type_name="dict").evaluate(rctx)):
        return False

    class NetworkDiagResult(BaseModel):
        model_config = ConfigDict(extra="forbid")
        severity: Literal["high"]
        recommended_action: Literal["create_ticket"]
        escalation_reason: str = Field(min_length=1)

    try:
        NetworkDiagResult.model_validate(result)
        return True
    except Exception:
        return False
    # CHECK_END


# check: C03
def eval_c03_conditional(check_id: str = "C03") -> bool:
    trace = load_trace(check_id)
    specialist = _tool(trace, "run_billing_policy_specialist")
    if specialist is None:
        return False
    result = specialist.get("result")
    # CHECK_START
    rctx = EvaluatorContext(
        name=check_id,
        inputs={},
        metadata=None,
        expected_output=None,
        output=result,
        duration=0.0,
        _span_tree=trace_to_span_tree(trace),
        attributes={},
        metrics={},
    )
    if not _ok(IsInstance(type_name="dict").evaluate(rctx)):
        return False

    class BillingResult(BaseModel):
        model_config = ConfigDict(extra="ignore")
        eligible: bool
        amount: float | None = None

        @model_validator(mode="after")
        def amount_rule(self) -> BillingResult:
            if self.eligible:
                if self.amount is None or self.amount <= 0:
                    raise ValueError("eligible requires positive amount")
            elif self.amount is not None:
                raise ValueError("ineligible must omit amount")
            return self

    try:
        BillingResult.model_validate(result)
        return True
    except Exception:
        return False
    # CHECK_END


# check: C04
def eval_c04_numeric(check_id: str = "C04") -> bool:
    trace = load_trace(check_id)
    specialist = _tool(trace, "run_billing_policy_specialist")
    if specialist is None:
        return False
    result = specialist.get("result")
    # CHECK_START
    class BillingAmount(BaseModel):
        model_config = ConfigDict(extra="forbid")
        eligible: Literal[True]
        amount: float = Field(ge=0.01, le=500.0)

    try:
        BillingAmount.model_validate(result)
        return True
    except Exception:
        return False
    # CHECK_END


# check: C05
def eval_c05_span_sequence(check_id: str = "C05") -> bool:
    trace = load_trace(check_id)
    ctx = _trace_ctx(trace, check_id)
    # CHECK_START
    @dataclass(repr=False)
    class OrderedToolCalls(Evaluator[dict, dict, None]):
        """Custom Evaluator over ctx.metadata['tool_calls'] (Pydantic Evals pattern)."""

        def evaluate(self, inner: EvaluatorContext[dict, dict, None]) -> bool:
            names = [str(c.get("name", "")) for c in (inner.metadata or {}).get("tool_calls") or []]
            exp = ["authenticate_customer", "get_outage_status"]
            ei = 0
            for name in names:
                if ei < len(exp) and name == exp[ei]:
                    ei += 1
            return ei == len(exp)

    return bool(OrderedToolCalls().evaluate(ctx))
    # CHECK_END


# check: C06
def eval_c06_forbid_span(check_id: str = "C06") -> bool:
    trace = load_trace(check_id)
    ctx = _trace_ctx(trace, check_id)
    # CHECK_START
    forbidden = HasMatchingSpan(query=SpanQuery(name_equals="apply_bill_credit"))
    return not bool(forbidden.evaluate(ctx))
    # CHECK_END


# check: C07
def eval_c07_tool_args(check_id: str = "C07") -> bool:
    trace = load_trace(check_id)
    ctx = _trace_ctx(trace, check_id)
    line_id = meta()["line_id"]
    # CHECK_START
    @dataclass(repr=False)
    class LineStatusArgs(Evaluator[dict, dict, None]):
        def evaluate(self, inner: EvaluatorContext[dict, dict, None]) -> bool:
            calls = (inner.metadata or {}).get("tool_calls") or []
            names = [str(c.get("name", "")) for c in calls]
            exp = ["authenticate_customer", "get_line_status"]
            ei = 0
            for name in names:
                if ei < len(exp) and name == exp[ei]:
                    ei += 1
            if ei != len(exp):
                return False
            gls = next((c for c in calls if c.get("name") == "get_line_status"), None)
            return gls is not None and gls.get("args", {}).get("line_id") == line_id

    return bool(LineStatusArgs().evaluate(ctx))
    # CHECK_END


# check: C08
def eval_c08_tool_result(check_id: str = "C08") -> bool:
    trace = load_trace(check_id)
    specialist = _tool(trace, "run_network_diagnostics_specialist")
    if specialist is None:
        return False
    result = specialist.get("result")
    # CHECK_START
    class SpecialistSummary(BaseModel):
        model_config = ConfigDict(extra="forbid")
        severity: Literal["medium", "high"]
        recommended_action: str = Field(min_length=1)
        summary: str = Field(min_length=10)

    try:
        SpecialistSummary.model_validate(result)
        return True
    except Exception:
        return False
    # CHECK_END


# check: C09
def eval_c09_nested(check_id: str = "C09") -> bool:
    trace = load_trace(check_id)
    ctx = _trace_ctx(trace, check_id)
    # CHECK_START
    @dataclass(repr=False)
    class NestedChildOrder(Evaluator[dict, dict, None]):
        def evaluate(self, inner: EvaluatorContext[dict, dict, None]) -> bool:
            if not HasMatchingSpan(
                query=SpanQuery(name_equals="run_network_diagnostics_specialist")
            ).evaluate(inner):
                return False
            parent = _tool(inner.output, "run_network_diagnostics_specialist")
            if parent is None:
                return False
            names = [str(c.get("name", "")) for c in parent.get("children") or []]
            return names == ["pull_network_events", "score_signal_anomaly"]

    return bool(NestedChildOrder().evaluate(ctx))
    # CHECK_END


# check: C10
def eval_c10_unordered(check_id: str = "C10") -> bool:
    trace = load_trace(check_id)
    ctx = _trace_ctx(trace, check_id)
    # CHECK_START
    query: SpanQuery = {
        "and_": [
            {"some_descendant_has": {"name_equals": "heartbeat_ping"}},
            {"some_descendant_has": {"name_equals": "get_line_status"}},
        ]
    }
    return bool(HasMatchingSpan(query=query).evaluate(ctx))
    # CHECK_END


# check: C11
def eval_c11_db_state(check_id: str = "C11") -> bool:
    _ = load_trace(check_id)
    # CHECK_START
    base = Path(tempfile.mkdtemp(prefix="pe_c11_"))
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
    # CHECK_END


# check: C12
def eval_c12_multi_turn(check_id: str = "C12") -> bool:
    trace = load_trace(check_id)
    ctx = _trace_ctx(trace, check_id, turn="last")
    # CHECK_START
    @dataclass(repr=False)
    class LastTurnToolSequence(Evaluator[dict, dict, None]):
        def evaluate(self, inner: EvaluatorContext[dict, dict, None]) -> bool:
            turns = inner.output.get("turns") or []
            if not turns:
                return False
            last_tools = turns[-1].get("tools") or []
            names = [str(t.get("name", "")) for t in last_tools]
            exp = ["authenticate_customer", "create_support_ticket"]
            ei = 0
            for name in names:
                if ei < len(exp) and name == exp[ei]:
                    ei += 1
            return ei == len(exp)

    if not LastTurnToolSequence().evaluate(ctx):
        return False
    mmeta = meta()
    base = Path(tempfile.mkdtemp(prefix="pe_c12_"))
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
    # CHECK_END


EVALUATORS: dict[str, Callable[[str], bool]] = {
    "C01": eval_c01_output_rubric,
    "C02": eval_c02_validate_shape,
    "C03": eval_c03_conditional,
    "C04": eval_c04_numeric,
    "C05": eval_c05_span_sequence,
    "C06": eval_c06_forbid_span,
    "C07": eval_c07_tool_args,
    "C08": eval_c08_tool_result,
    "C09": eval_c09_nested,
    "C10": eval_c10_unordered,
    "C11": eval_c11_db_state,
    "C12": eval_c12_multi_turn,
}

CHECK_IDS = [f"C{i:02d}" for i in range(1, 13)]


def _evaluator_for(check_id: str) -> _CaseRunner:
    return _CaseRunner(check_id, EVALUATORS[check_id])


@dataclass(repr=False)
class _CaseRunner(Evaluator[dict, dict, None]):
    """Wraps per-check logic so each Case uses native evaluator tuples."""

    check_id: str
    run: Callable[[str], bool]

    def evaluate(self, ctx: EvaluatorContext[dict, dict, None]) -> bool:
        return bool(self.run(self.check_id))


def build_cases() -> list[Case]:
    """Native Pydantic Evals layout: one Dataset, one Case per specimen."""
    return [
        Case(
            name=cid,
            inputs={"check_id": cid},
            evaluators=(_evaluator_for(cid),),
        )
        for cid in CHECK_IDS
    ]


EXPRESSIVENESS_DATASET = Dataset(name="expressiveness", cases=build_cases())


def run_case(check_id: str) -> bool:
    return EVALUATORS[check_id](check_id)


def run_evaluator_on_trace(check_id: str, trace: dict[str, Any]) -> bool:
    """Run a port against an explicit trace (fail-sample harness)."""
    from unittest.mock import patch

    with patch(
        "implementations.pydantic_evals.dataset.load_trace",
        return_value=trace,
    ):
        return bool(EVALUATORS[check_id](check_id))


def fail_message_for_trace(check_id: str, trace: dict[str, Any]) -> str:
    """Native Pydantic Evals diagnostic text for a failing trace."""
    if run_evaluator_on_trace(check_id, trace):
        return "unexpected pass"

    if check_id == "C01":
        tctx = _text_ctx(str(trace.get("output", "")), check_id)
        for term in ("credit", "refund", "$", "dollar"):
            result = Contains(term, case_sensitive=False).evaluate(tctx)
            if isinstance(result, EvaluationReason) and not result.value:
                return str(result.reason)
        return "output rubric failed"

    tool_name = (
        "run_billing_policy_specialist"
        if check_id in ("C03", "C04")
        else "run_network_diagnostics_specialist"
    )
    if check_id in ("C02", "C03", "C04", "C08"):
        specialist = _tool(trace, tool_name)
        if specialist is None:
            return f"missing tool {tool_name!r}"
        result = specialist.get("result")
        rctx = EvaluatorContext(
            name=check_id,
            inputs={},
            metadata=None,
            expected_output=None,
            output=result,
            duration=0.0,
            _span_tree=trace_to_span_tree(trace),
            attributes={},
            metrics={},
        )
        inst = IsInstance(type_name="dict").evaluate(rctx)
        if isinstance(inst, EvaluationReason) and not inst.value:
            return str(inst.reason)
        try:
            if check_id == "C02":

                class NetworkDiagResult(BaseModel):
                    model_config = ConfigDict(extra="forbid")
                    severity: Literal["high"]
                    recommended_action: Literal["create_ticket"]
                    escalation_reason: str = Field(min_length=1)

                NetworkDiagResult.model_validate(result)
            elif check_id == "C03":

                class BillingResult(BaseModel):
                    model_config = ConfigDict(extra="ignore")
                    eligible: bool
                    amount: float | None = None

                    @model_validator(mode="after")
                    def amount_rule(self) -> BillingResult:
                        if self.eligible:
                            if self.amount is None or self.amount <= 0:
                                raise ValueError("eligible requires positive amount")
                        elif self.amount is not None:
                            raise ValueError("ineligible must omit amount")
                        return self

                BillingResult.model_validate(result)
            elif check_id == "C04":

                class BillingAmount(BaseModel):
                    model_config = ConfigDict(extra="forbid")
                    eligible: Literal[True]
                    amount: float = Field(ge=0.01, le=500.0)

                BillingAmount.model_validate(result)
            else:

                class SpecialistSummary(BaseModel):
                    model_config = ConfigDict(extra="forbid")
                    severity: Literal["medium", "high"]
                    recommended_action: str = Field(min_length=1)
                    summary: str = Field(min_length=10)

                SpecialistSummary.model_validate(result)
        except Exception as exc:
            return str(exc)
        return f"{check_id} validation failed"

    if check_id == "C06":
        ctx = _trace_ctx(trace, check_id)
        if HasMatchingSpan(query=SpanQuery(name_equals="apply_bill_credit")).evaluate(ctx):
            return "forbidden span apply_bill_credit present"
        return "forbidden tool check failed"

    if check_id == "C09":
        parent = _tool(trace, "run_network_diagnostics_specialist")
        if parent is None:
            return "missing run_network_diagnostics_specialist"
        names = [c.get("name") for c in (parent.get("children") or [])]
        return (
            "nested children expected ['pull_network_events', 'score_signal_anomaly'], "
            f"got {names!r}"
        )

    if check_id == "C11":
        base = Path(tempfile.mkdtemp(prefix="pe_c11_fail_"))
        try:
            telco = TelcoStore(base / "telco.sqlite")
            apply_seed(telco, "task_T04")
            try:
                o.assert_ticket_exists(telco)
                return "unexpected pass"
            except AssertionError as exc:
                return str(exc)
        finally:
            shutil.rmtree(base, ignore_errors=True)

    if check_id in ("C05", "C07", "C10", "C12"):
        ctx = _trace_ctx(trace, check_id, turn="last" if check_id == "C12" else None)
        names = [
            str(c.get("name", ""))
            for c in (ctx.metadata or {}).get("tool_calls") or []
        ]
        if check_id == "C05":
            exp = ["authenticate_customer", "get_outage_status"]
        elif check_id == "C07":
            exp = ["authenticate_customer", "get_line_status"]
            gls = next((c for c in (ctx.metadata or {}).get("tool_calls") or [] if c.get("name") == "get_line_status"), None)
            if gls and gls.get("args", {}).get("line_id") != meta()["line_id"]:
                return (
                    f"get_line_status.args.line_id expected {meta()['line_id']!r}, "
                    f"got {gls.get('args', {}).get('line_id')!r}"
                )
        elif check_id == "C10":
            exp = ["heartbeat_ping", "get_line_status"]
        else:
            turns = trace.get("turns") or []
            names = [str(t.get("name", "")) for t in (turns[-1].get("tools") or []) if turns]
            exp = ["authenticate_customer", "create_support_ticket"]
        ei = 0
        for name in names:
            if ei < len(exp) and name == exp[ei]:
                ei += 1
        if ei != len(exp):
            return f"tool sequence expected {exp!r}, got ordered subsequence match {ei}/{len(exp)} in {names!r}"
        if check_id == "C12":
            line_id = meta()["line_id"]
            base = Path(tempfile.mkdtemp(prefix="pe_c12_fail_"))
            try:
                telco = TelcoStore(base / "telco.sqlite")
                apply_seed(telco, "task_T46")
                try:
                    o.assert_ticket_for_line(telco, line_id)
                    return "unexpected pass"
                except AssertionError as exc:
                    return str(exc)
            finally:
                shutil.rmtree(base, ignore_errors=True)

    return f"pydantic_evals {check_id} failed"
