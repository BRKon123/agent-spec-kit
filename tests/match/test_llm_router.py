from __future__ import annotations

import asyncio

import pytest

from agent_spec_kit.judges.base import LLMCriteriaJudgeResult
from agent_spec_kit.judges.router import judge_criteria, parse_model_route


def test_parse_model_route() -> None:
    provider, model = parse_model_route("openai:gpt-5-nano")
    assert provider == "openai"
    assert model == "gpt-5-nano"


def test_parse_model_route_requires_prefix() -> None:
    with pytest.raises(ValueError):
        parse_model_route("gpt-5-nano")


def test_judge_criteria_accepts_injected_dict() -> None:
    def judge_fn(_actual: str, criteria: tuple[str, ...], _ctx: str | None):
        return {
            "criteria": [
                {"passed": True, "rationale": f"hit-{i}"}
                for i, _ in enumerate(criteria)
            ]
        }

    result = asyncio.run(
        judge_criteria(
            actual="x",
            criteria=("a", "b"),
            model="openai:gpt-5-nano",
            judge_fn=judge_fn,
        )
    )
    assert isinstance(result, LLMCriteriaJudgeResult)
    assert result.passed_count == 2


def test_judge_criteria_single_requires_exact_length() -> None:
    def judge_fn(_actual: str, _criteria: tuple[str, ...], _ctx: str | None):
        return {
            "criteria": [
                {"passed": True, "rationale": "ok"},
                {"passed": True, "rationale": "ok"},
                {"passed": True, "rationale": "extra"},
            ]
        }

    with pytest.raises(ValueError, match="length mismatch"):
        asyncio.run(
            judge_criteria(
                actual="x",
                criteria=("a", "b"),
                model="openai:gpt-5-nano",
                judge_fn=judge_fn,
                evaluation_mode="single",
            )
        )
