"""Tests for check(), match(), and basic coercion."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import pytest

import agent_spec_kit.match as m


def test_check_requires_actual_and_accepts_keyword() -> None:
    with pytest.raises(TypeError, match="requires the value"):
        m.check(1)  # type: ignore[call-arg]
    assert m.check(1, actual=1).ok


def test_match_literal_equality() -> None:
    r = m.check(42, 42)
    assert r.ok
    r2 = m.check("hi", "there")
    assert not r2.ok
    assert any(e.code == "equality" for e in r2.errors)


def test_coerce_dict_and_list_literal_specs() -> None:
    spec = {
        "items": [1, {"tag": "x"}],
        "meta": {"ok": True},
    }
    actual = {
        "items": [1, {"tag": "x"}],
        "meta": {"ok": True},
    }
    r = m.check(spec, actual)
    assert r.ok


def test_predicate_and_message() -> None:
    r = m.check(lambda x: x > 10, 3)
    assert not r.ok
    p = m.match(lambda x: x > 10, message="must be > 10")
    assert isinstance(p, m.PredicateMatcher)
    r2 = m.check(p, 12)
    assert r2.ok
    r3 = m.check(p, 2)
    assert not r3.ok
    assert r3.errors[0].message == "must be > 10"


def test_single_arg_match_returns_matcher() -> None:
    inner = m.match(3)
    assert m.check(inner, 3).ok


def test_typeerror_unknown_coercion() -> None:
    with pytest.raises(TypeError):
        m.match(object())  # noqa: B009 — builtin instance, not a matcher


def test_async_check_accepts_sync_matchers() -> None:
    r = asyncio.run(m.async_check("ok", "ok"))
    assert r.ok


def test_llm_criteria_passes_threshold_with_judge_fn() -> None:
    def judge_fn(actual: str, criteria: Sequence[str], _ctx: str | None):
        assert "incident" in actual
        return {
            "criteria": [
                {"passed": True, "rationale": "root cause present"},
                {"passed": True, "rationale": "impact present"},
                {"passed": False, "rationale": "no next steps"},
            ]
        }

    matcher = m.llm_criteria(
        criteria=[
            "States root cause",
            "Mentions impact",
            "Lists next steps",
        ],
        threshold=2,
        model="openai:gpt-5-nano",
        judge_fn=judge_fn,
    )
    r = asyncio.run(m.async_check(matcher, "incident summary text"))
    assert r.ok


def test_llm_criteria_fails_threshold_with_details() -> None:
    async def judge_fn(_actual: str, _criteria: Sequence[str], _ctx: str | None):
        return {
            "criteria": [
                {"passed": False, "rationale": "wrong"},
                {"passed": True, "rationale": "good"},
                {"passed": False, "rationale": "missing"},
            ]
        }

    matcher = m.llm_criteria(
        criteria=["a", "b", "c"],
        threshold=2,
        model="openai:gpt-5-nano",
        judge_fn=judge_fn,
    )
    r = asyncio.run(m.async_check(matcher, "candidate output"))
    assert not r.ok
    assert r.errors[0].code == "llm_criteria_threshold"
    assert r.errors[0].witness_json is not None


def test_nested_async_matcher_inside_tool_call_result() -> None:
    async def judge_fn(_actual: str, _criteria: Sequence[str], _ctx: str | None):
        return {"criteria": [{"passed": True, "rationale": "contains 20"}]}

    spec = m.list(
        [
            m.tool_call(
                "multiply_numbers",
                args={"a": 4, "b": 5},
                result=m.llm_criteria(
                    criteria=["contains 20"],
                    threshold=1,
                    model="openai:gpt-5-nano",
                    judge_fn=judge_fn,
                ),
            )
        ],
        mode="ordered",
        allow_extras=True,
    )
    actual = [
        {
            "name": "multiply_numbers",
            "args": {"a": 4, "b": 5},
            "result": "20",
            "error": None,
            "children": [],
            "metadata": {},
        }
    ]
    r = asyncio.run(m.async_check(spec, actual))
    assert r.ok


def test_all_of_and_not_sync() -> None:
    r = m.check(m.all_of(m.contains("hello"), m.not_(m.contains("bye"))), "hello there")
    assert r.ok
    r2 = m.check(m.all_of(m.contains("hello"), m.not_(m.contains("bye"))), "hello bye")
    assert not r2.ok
    assert any(e.code == "not" for e in r2.errors)


def test_all_of_with_nested_async_matcher() -> None:
    async def judge_fn(_actual: str, _criteria: Sequence[str], _ctx: str | None):
        return {"criteria": [{"passed": True, "rationale": "ok"}]}

    spec = m.all_of(
        m.contains("incident"),
        m.llm_criteria(
            criteria=["mentions incident"],
            threshold=1,
            model="openai:gpt-5-nano",
            judge_fn=judge_fn,
        ),
    )
    r = asyncio.run(m.async_check(spec, "incident summary"))
    assert r.ok


def test_contains_is_case_insensitive_by_default() -> None:
    r = m.check(m.contains("hello"), "HeLLo there")
    assert r.ok


def test_contains_can_be_case_sensitive() -> None:
    ok = m.check(m.contains("Hello", case_sensitive=True), "Hello there")
    assert ok.ok

    fail = m.check(m.contains("hello", case_sensitive=True), "Hello there")
    assert not fail.ok
