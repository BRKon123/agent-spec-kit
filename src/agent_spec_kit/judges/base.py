"""Shared datatypes for LLM criteria judging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CRITERIA_JUDGE_SYSTEM_PROMPT = (
    "You are a strict output evaluator. "
    "Each criterion should be checked as a concrete pass/fail rule about the output text, "
    "some example criteria: 'output contains 23' or 'output mentions snails'. "
    "Judge each criterion independently and do not invent new criteria."
)


@dataclass(frozen=True, slots=True)
class CriterionJudgement:
    index: int
    criterion: str
    passed: bool
    rationale: str


@dataclass(frozen=True, slots=True)
class LLMCriteriaJudgeResult:
    criteria: tuple[CriterionJudgement, ...]
    passed_count: int
    model: str

    @staticmethod
    def from_mapping(
        payload: dict[str, Any],
        *,
        expected_criteria: tuple[str, ...],
        model: str,
        require_exact_len: bool = False,
    ) -> "LLMCriteriaJudgeResult":
        rows = payload.get("criteria")
        if not isinstance(rows, list):
            raise ValueError("judge response must contain list field 'criteria'")
        if require_exact_len and len(rows) != len(expected_criteria):
            raise ValueError(
                "judge response criteria length mismatch: "
                f"got {len(rows)}, expected {len(expected_criteria)}"
            )
        judged: list[CriterionJudgement] = []
        for i, criterion in enumerate(expected_criteria):
            if i >= len(rows) or not isinstance(rows[i], dict):
                raise ValueError(f"judge response missing criteria[{i}]")
            row = rows[i]
            passed = bool(row.get("passed"))
            rationale = str(row.get("rationale", "")).strip()
            judged.append(
                CriterionJudgement(
                    index=i,
                    criterion=criterion,
                    passed=passed,
                    rationale=rationale,
                )
            )
        passed_count = sum(1 for c in judged if c.passed)
        return LLMCriteriaJudgeResult(criteria=tuple(judged), passed_count=passed_count, model=model)


__all__ = ["CriterionJudgement", "LLMCriteriaJudgeResult", "CRITERIA_JUDGE_SYSTEM_PROMPT"]
