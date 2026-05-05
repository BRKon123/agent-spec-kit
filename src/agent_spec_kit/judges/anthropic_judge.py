"""Anthropic adapter for criteria judging."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from pydantic import BaseModel

from agent_spec_kit.judges.base import CRITERIA_JUDGE_SYSTEM_PROMPT, LLMCriteriaJudgeResult
from agent_spec_kit.judges.structured import call_structured


class _CriterionRow(BaseModel):
    passed: bool
    rationale: str


class _CriteriaResponse(BaseModel):
    criteria: list[_CriterionRow]


def _build_prompt(actual: str, criteria: Sequence[str], judge_context: str | None) -> str:
    criteria_lines = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(criteria))
    context = f"\nContext:\n{judge_context}\n" if judge_context else ""
    return (
        "Evaluate the candidate output against each criterion.\n"
        "Return JSON only with key 'criteria', each item has:\n"
        "- passed (boolean)\n"
        "- rationale (short string)\n\n"
        f"{context}"
        f"Criteria:\n{criteria_lines}\n\n"
        f"Candidate output:\n{actual}"
    )


async def judge_with_anthropic(
    *,
    actual: str,
    criteria: tuple[str, ...],
    model: str,
    model_route: str,
    temperature: float | None,
    timeout_s: float | None,
    judge_context: str | None,
    evaluation_mode: str,
) -> LLMCriteriaJudgeResult:
    if evaluation_mode == "single":
        parsed = await call_structured(
            model=model_route,
            system=CRITERIA_JUDGE_SYSTEM_PROMPT + " Return JSON only.",
            user=_build_prompt(actual, criteria, judge_context),
            response_model=_CriteriaResponse,
            temperature=temperature,
            timeout_s=timeout_s,
        )
        payload = {"criteria": [row.model_dump() for row in parsed.criteria]}
        return LLMCriteriaJudgeResult.from_mapping(
            payload,
            expected_criteria=criteria,
            model=model_route,
            require_exact_len=True,
        )

    if evaluation_mode != "per_criterion":
        raise ValueError(f"unsupported evaluation_mode {evaluation_mode!r}")

    async def _judge_single(criterion: str) -> dict[str, object]:
        parsed = await call_structured(
            model=model_route,
            system=CRITERIA_JUDGE_SYSTEM_PROMPT + " Return JSON only.",
            user=_build_prompt(actual, [criterion], judge_context),
            response_model=_CriteriaResponse,
            temperature=temperature,
            timeout_s=timeout_s,
        )
        if not parsed.criteria:
            raise RuntimeError("Anthropic per-criterion judge returned empty structured response")
        row = parsed.criteria[0]
        return {"passed": row.passed, "rationale": row.rationale}

    rows = await asyncio.gather(*(_judge_single(criterion) for criterion in criteria))
    return LLMCriteriaJudgeResult.from_mapping(
        {"criteria": list(rows)},
        expected_criteria=criteria,
        model=model_route,
    )


__all__ = ["judge_with_anthropic", "_CriteriaResponse", "_CriterionRow"]
