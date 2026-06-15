"""DeepEval BaseMetric wrapper for diagnostic slot checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from scripts.diagnostic_quality_lib import FailureWitness


class SlotAssertMetric(BaseMetric):
    """Run a slot check function inside DeepEval's BaseMetric.measure()."""

    def __init__(
        self,
        check_fn: Callable[[dict[str, Any], FailureWitness], None],
        artifact: dict[str, Any],
        witness: FailureWitness,
        *,
        threshold: float = 0.5,
    ) -> None:
        self.check_fn = check_fn
        self.artifact = artifact
        self.witness = witness
        self.threshold = threshold
        self.async_mode = False
        self.include_reason = True

    def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
        _ = test_case
        try:
            self.check_fn(self.artifact, self.witness)
            self.score = 1.0
            self.success = True
        except AssertionError as exc:
            self.score = 0.0
            self.success = False
            msg = str(exc).strip() or "AssertionError"
            self.reason = msg if msg.startswith("Assertion") else f"AssertionError: {msg}"
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            raise AssertionError(self.error)
        return bool(self.success)


def metric_message(metric: SlotAssertMetric) -> str:
    if metric.reason:
        return str(metric.reason).strip()
    if metric.error:
        return str(metric.error).strip()
    return f"score={metric.score}"


def run_slot_check(
    check_fn: Callable[[dict[str, Any], FailureWitness], None],
    artifact: dict[str, Any],
    witness: FailureWitness,
    *,
    key: str,
) -> dict[str, Any]:
    metric = SlotAssertMetric(check_fn, artifact, witness)
    metric.measure(LLMTestCase(input=key, actual_output=""))
    ok = bool(metric.is_successful())
    return {
        "key": key,
        "score": 1 if ok else 0,
        "comment": metric_message(metric) if not ok else "",
    }
