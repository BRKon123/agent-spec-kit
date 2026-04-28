"""LLM-based criteria matcher with threshold scoring."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.judges.base import LLMCriteriaJudgeResult
from agent_spec_kit.judges.router import judge_criteria
from agent_spec_kit.match.protocol import BaseMatcher
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr

JudgeFn = Callable[[str, Sequence[str], str | None], Any]


@dataclass(frozen=True, slots=True)
class LLMCriteriaMatcher(BaseMatcher):
    criteria: tuple[str, ...]
    threshold: int
    model: str
    temperature: float | None = None
    timeout_s: float | None = None
    judge_context: str | None = None
    judge_fn: JudgeFn | None = None
    evaluation_mode: str = "single"

    def __post_init__(self) -> None:
        if not self.criteria:
            raise ValueError("criteria must contain at least one item")
        if any(not c.strip() for c in self.criteria):
            raise ValueError("criteria must not contain empty strings")
        if self.threshold < 1:
            raise ValueError("threshold must be >= 1")
        if self.threshold > len(self.criteria):
            raise ValueError("threshold must be <= number of criteria")
        if ":" not in self.model:
            raise ValueError("model must be provider-prefixed, e.g. 'openai:gpt-5-nano'")
        if self.evaluation_mode not in {"single", "per_criterion"}:
            raise ValueError("evaluation_mode must be 'single' or 'per_criterion'")

    def check(self, actual: Any, path: Path) -> MatchResult:
        msg = (
            "llm_criteria requires async evaluation; use match.async_check(...) or "
            "scenario.materialise()/async_check_output"
        )
        return MatchResult.failure(
            MatchError(
                path=path,
                code="llm_criteria_async_required",
                message=msg,
                expected="async matcher execution",
                actual=type(actual).__name__,
            )
        )

    async def async_check(self, actual: Any, path: Path) -> MatchResult:
        actual_text = actual if isinstance(actual, str) else _short_repr(actual, max_len=10000)
        judged = await judge_criteria(
            actual=actual_text,
            criteria=self.criteria,
            model=self.model,
            temperature=self.temperature,
            timeout_s=self.timeout_s,
            judge_context=self.judge_context,
            judge_fn=self.judge_fn,
            evaluation_mode=self.evaluation_mode,
        )
        if judged.passed_count >= self.threshold:
            return MatchResult.success()
        failed = [g for g in judged.criteria if not g.passed]
        details = {
            "passed_count": judged.passed_count,
            "threshold": self.threshold,
            "model": judged.model,
            "failed_criteria": [
                {
                    "index": g.index,
                    "criterion": g.criterion,
                    "rationale": g.rationale,
                }
                for g in failed
            ],
        }
        return MatchResult.failure(
            MatchError(
                path=path,
                code="llm_criteria_threshold",
                message=(
                    f"LLM criteria threshold failed: passed {judged.passed_count}/{len(self.criteria)} "
                    f"(required {self.threshold})"
                ),
                expected=f"passed_count >= {self.threshold}",
                actual=str(judged.passed_count),
                witness_json=json.dumps(details, ensure_ascii=True),
            )
        )


def llm_criteria_matcher(
    *,
    criteria: Sequence[str],
    threshold: int,
    model: str,
    temperature: float | None = None,
    timeout_s: float | None = None,
    judge_context: str | None = None,
    judge_fn: JudgeFn | None = None,
    evaluation_mode: str = "single",
) -> LLMCriteriaMatcher:
    return LLMCriteriaMatcher(
        criteria=tuple(criteria),
        threshold=threshold,
        model=model,
        temperature=temperature,
        timeout_s=timeout_s,
        judge_context=judge_context,
        judge_fn=judge_fn,
        evaluation_mode=evaluation_mode,
    )


__all__ = ["LLMCriteriaMatcher", "llm_criteria_matcher", "JudgeFn"]
