"""Tests for check(), match(), and basic coercion."""

from __future__ import annotations

import asyncio
import json
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
    assert (
        "Failed criteria:\n"
        "- [0] criterion: a\n"
        "  rationale: wrong\n"
        "- [2] criterion: c\n"
        "  rationale: missing"
    ) in r.errors[0].message
    assert r.errors[0].witness_json is not None


def test_llm_criteria_default_threshold_requires_all_criteria() -> None:
    async def judge_fn(_actual: str, _criteria: Sequence[str], _ctx: str | None):
        return {
            "criteria": [
                {"passed": True, "rationale": "good"},
                {"passed": False, "rationale": "missing"},
            ]
        }

    matcher = m.llm_criteria(
        criteria=["a", "b"],
        model="openai:gpt-5-nano",
        judge_fn=judge_fn,
    )
    r = asyncio.run(m.async_check(matcher, "candidate output"))
    assert not r.ok
    assert r.errors[0].expected == "passed_count >= 2"


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


def test_one_of_failure_propagates_inner_error() -> None:
    r = m.check(m.one_of(1, m.string(min_len=5)), 3)
    assert not r.ok
    assert r.errors[0].code == "one_of"
    assert "one_of:" in r.errors[0].message
    assert "does not equal expected" in r.errors[0].message
    assert len(r.errors) >= 2
    assert r.errors[1].code == "equality"
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["inner_error"]["code"] == "equality"


def test_all_of_failure_propagates_inner_error() -> None:
    r = m.check(m.all_of(m.contains("hello"), m.contains("bye")), "hello there")
    assert not r.ok
    assert r.errors[0].code == "all_of"
    assert "all_of:" in r.errors[0].message
    assert "substring" in r.errors[0].message.lower() or "contain" in r.errors[0].message.lower()
    assert any(e.code == "predicate" for e in r.errors[1:])
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert "inner_error" in witness


def test_all_of_nested_not_failure_propagates_not_and_contains() -> None:
    r = m.check(m.all_of(m.contains("hello"), m.not_(m.contains("bye"))), "hello bye")
    assert not r.ok
    assert r.errors[0].code == "all_of"
    assert "all_of:" in r.errors[0].message
    assert "not:" in r.errors[0].message
    assert any(e.code == "not" for e in r.errors)


def test_tool_call_plain_dict_args_ignores_extra_keys() -> None:
    spec = m.tool_call("get_line_status", args={"line_id": "LINE-001"})
    actual = {"name": "get_line_status", "args": {"line_id": "LINE-001", "verbose": True}}
    assert m.check(spec, actual).ok


def test_tool_call_plain_dict_args_rejects_wrong_listed_key() -> None:
    spec = m.tool_call("get_line_status", args={"line_id": "LINE-001"})
    actual = {"name": "get_line_status", "args": {"line_id": "LINE-999"}}
    r = m.check(spec, actual)
    assert not r.ok
    assert any(e.path == ("args", "line_id") for e in r.errors)


def test_tool_call_explicit_object_forbid_rejects_extra_arg_keys() -> None:
    spec = m.tool_call(
        "get_line_status",
        args=m.object({"line_id": "LINE-001"}, extra="forbid"),
    )
    actual = {"name": "get_line_status", "args": {"line_id": "LINE-001", "verbose": True}}
    r = m.check(spec, actual)
    assert not r.ok
    assert any(e.code == "extra_key" and e.path == ("args", "verbose") for e in r.errors)
