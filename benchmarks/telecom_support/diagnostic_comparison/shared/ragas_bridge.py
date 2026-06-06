"""Ragas collections BaseMetric wrapper for diagnostic slot checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ragas.metrics.collections.base import BaseMetric as RagasBaseMetric
from ragas.metrics.result import MetricResult

from scripts.diagnostic_quality_lib import FailureWitness


class SlotAssertMetric(RagasBaseMetric):
    """Run a slot check function inside Ragas BaseMetric.score()."""

    def __init__(
        self,
        check_fn: Callable[[dict[str, Any], FailureWitness], None],
        artifact: dict[str, Any],
        witness: FailureWitness,
        *,
        name: str = "slot_assert",
        **kwargs: Any,
    ) -> None:
        self.check_fn = check_fn
        self.artifact = artifact
        self.witness = witness
        super().__init__(name=name, **kwargs)

    async def ascore(self) -> MetricResult:
        try:
            self.check_fn(self.artifact, self.witness)
            return MetricResult(value=1.0)
        except AssertionError as exc:
            msg = str(exc).strip() or "AssertionError"
            reason = msg if msg.startswith("Assertion") else f"AssertionError: {msg}"
            return MetricResult(value=0.0, reason=reason)


def metric_message(result: MetricResult) -> str:
    if result.reason:
        return str(result.reason).strip()
    return str(result.value)


def run_slot_check(
    check_fn: Callable[[dict[str, Any], FailureWitness], None],
    artifact: dict[str, Any],
    witness: FailureWitness,
    *,
    key: str,
) -> dict[str, Any]:
    metric = SlotAssertMetric(check_fn, artifact, witness, name=key)
    result = metric.score()
    ok = float(result.value) >= 1.0
    return {
        "key": key,
        "score": 1 if ok else 0,
        "comment": metric_message(result) if not ok else "",
    }
