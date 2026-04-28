"""Model-string routing for criteria judges."""

from __future__ import annotations

import inspect
from collections.abc import Sequence
from typing import Any

from agent_spec_kit.judges.base import LLMCriteriaJudgeResult


def parse_model_route(model: str) -> tuple[str, str]:
    if ":" not in model:
        raise ValueError("model must be provider-prefixed, e.g. 'openai:gpt-5-nano'")
    provider, model_name = model.split(":", 1)
    provider = provider.strip().lower()
    model_name = model_name.strip()
    if not provider or not model_name:
        raise ValueError("model must use '<provider>:<model_name>' format")
    return provider, model_name


async def judge_criteria(
    *,
    actual: str,
    criteria: Sequence[str],
    model: str,
    temperature: float | None = None,
    timeout_s: float | None = None,
    judge_context: str | None = None,
    judge_fn: Any | None = None,
    evaluation_mode: str = "single",
) -> LLMCriteriaJudgeResult:
    expected_criteria = tuple(criteria)
    if judge_fn is not None:
        raw = judge_fn(actual, expected_criteria, judge_context)
        if inspect.isawaitable(raw):
            raw = await raw
        if isinstance(raw, LLMCriteriaJudgeResult):
            return raw
        if isinstance(raw, dict):
            return LLMCriteriaJudgeResult.from_mapping(
                raw,
                expected_criteria=expected_criteria,
                model=model,
                require_exact_len=(evaluation_mode == "single"),
            )
        raise TypeError("judge_fn must return LLMCriteriaJudgeResult or dict")

    provider, model_name = parse_model_route(model)
    if provider == "openai":
        from agent_spec_kit.judges.openai_judge import judge_with_openai

        return await judge_with_openai(
            actual=actual,
            criteria=expected_criteria,
            model=model_name,
            model_route=model,
            temperature=temperature,
            timeout_s=timeout_s,
            judge_context=judge_context,
            evaluation_mode=evaluation_mode,
        )
    if provider == "anthropic":
        from agent_spec_kit.judges.anthropic_judge import judge_with_anthropic

        return await judge_with_anthropic(
            actual=actual,
            criteria=expected_criteria,
            model=model_name,
            model_route=model,
            temperature=temperature,
            timeout_s=timeout_s,
            judge_context=judge_context,
            evaluation_mode=evaluation_mode,
        )
    raise ValueError(f"unsupported model provider {provider!r} in {model!r}")


__all__ = ["judge_criteria", "parse_model_route"]
