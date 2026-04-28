"""Anthropic adapter for criteria judging."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence

from agent_spec_kit.judges.base import CRITERIA_JUDGE_SYSTEM_PROMPT, LLMCriteriaJudgeResult


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
    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:  # pragma: no cover - import guard
        raise RuntimeError("anthropic package is required for anthropic:* model routing") from e

    client = AsyncAnthropic(timeout=timeout_s)
    request_kwargs: dict[str, object] = {
        "model": model,
        "max_tokens": 1200,
        "system": CRITERIA_JUDGE_SYSTEM_PROMPT + " Return JSON only.",
    }
    if temperature is not None:
        request_kwargs["temperature"] = temperature

    if evaluation_mode == "single":
        response = await client.messages.create(
            **request_kwargs,
            messages=[{"role": "user", "content": _build_prompt(actual, criteria, judge_context)}],
        )
        text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        if not text_blocks:
            raise RuntimeError("Anthropic judge returned no text blocks")
        payload = json.loads(text_blocks[0])
        return LLMCriteriaJudgeResult.from_mapping(
            payload,
            expected_criteria=criteria,
            model=model_route,
            require_exact_len=True,
        )

    if evaluation_mode != "per_criterion":
        raise ValueError(f"unsupported evaluation_mode {evaluation_mode!r}")

    async def _judge_single(criterion: str) -> dict[str, object]:
        response = await client.messages.create(
            **request_kwargs,
            messages=[{"role": "user", "content": _build_prompt(actual, [criterion], judge_context)}],
        )
        text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        if not text_blocks:
            raise RuntimeError("Anthropic per-criterion judge returned no text blocks")
        payload = json.loads(text_blocks[0])
        parsed = LLMCriteriaJudgeResult.from_mapping(
            payload,
            expected_criteria=(criterion,),
            model=model_route,
            require_exact_len=True,
        )
        return {
            "passed": parsed.criteria[0].passed,
            "rationale": parsed.criteria[0].rationale,
        }
    rows = await asyncio.gather(*(_judge_single(criterion) for criterion in criteria))
    return LLMCriteriaJudgeResult.from_mapping(
        {"criteria": list(rows)},
        expected_criteria=criteria,
        model=model_route,
    )


__all__ = ["judge_with_anthropic"]
