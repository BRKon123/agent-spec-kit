"""Tests for check(), match(), and basic coercion."""

from __future__ import annotations

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
