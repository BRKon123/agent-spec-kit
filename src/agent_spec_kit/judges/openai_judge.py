"""OpenAI adapter for criteria judging."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pydantic import BaseModel
from typing import Any

from agent_spec_kit.judges.base import CRITERIA_JUDGE_SYSTEM_PROMPT, LLMCriteriaJudgeResult


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
        "Return strict JSON with key 'criteria' where each item has:\n"
        "- passed: boolean\n"
        "- rationale: short string\n\n"
        f"{context}"
        f"Criteria:\n{criteria_lines}\n\n"
        f"Candidate output:\n{actual}"
    )


async def judge_with_openai(
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
        from openai import AsyncOpenAI, BadRequestError
    except ImportError as e:  # pragma: no cover - import guard
        raise RuntimeError("openai package is required for openai:* model routing") from e

    client = AsyncOpenAI(timeout=timeout_s)
    
    async def _parse_response(messages: list[dict[str, str]]):
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "response_format": _CriteriaResponse,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            return await client.beta.chat.completions.parse(**kwargs)
        except BadRequestError as e:
            # Some models (e.g. gpt-5-nano variants) reject explicit temperature.
            msg = str(e).lower()
            if "temperature" not in msg or temperature is None:
                raise
            kwargs.pop("temperature", None)
            return await client.beta.chat.completions.parse(**kwargs)

    if evaluation_mode == "single":
        completion = await _parse_response(
            [
                {"role": "system", "content": CRITERIA_JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(actual, criteria, judge_context)},
            ]
        )
        message = completion.choices[0].message
        parsed = message.parsed
        if parsed is None:
            raise RuntimeError("OpenAI judge returned no structured parsed response")
        payload = {"criteria": [row.model_dump() for row in parsed.criteria]}
        return LLMCriteriaJudgeResult.from_mapping(
            payload,
            expected_criteria=criteria,
            model=model_route,
            require_exact_len=True,
        )

    if evaluation_mode != "per_criterion":
        raise ValueError(f"unsupported evaluation_mode {evaluation_mode!r}")

    async def _judge_single(criterion: str) -> dict[str, Any]:
        completion = await _parse_response(
            [
                {"role": "system", "content": CRITERIA_JUDGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_prompt(actual, [criterion], judge_context),
                },
            ]
        )
        message = completion.choices[0].message
        parsed = message.parsed
        if parsed is None or not parsed.criteria:
            raise RuntimeError("OpenAI per-criterion judge returned empty structured response")
        return parsed.criteria[0].model_dump()

    rows = await asyncio.gather(*(_judge_single(criterion) for criterion in criteria))
    return LLMCriteriaJudgeResult.from_mapping(
        {"criteria": list(rows)},
        expected_criteria=criteria,
        model=model_route,
        require_exact_len=False,
    )


__all__ = ["judge_with_openai"]
