"""Tests for agent_spec_kit.match — coercion, combinators, nested fixtures."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pytest
from pydantic import BaseModel

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


def test_object_optional_and_extra() -> None:
    spec = m.object(
        {
            "a": 1,
            "b": m.optional(m.string(min_len=1)),
        },
        extra="ignore",
    )
    assert m.check(spec, {"a": 1, "noise": 2}).ok
    assert not m.check(spec, {"b": "x"}).ok  # missing a
    spec2 = m.object({"a": 1}, extra="forbid")
    assert not m.check(spec2, {"a": 1, "x": 2}).ok
    assert any(e.code == "extra_key" for e in m.check(spec2, {"a": 1, "x": 2}).errors)


def test_rules_require_forbid_and_where() -> None:
    spec = m.object(
        {
            "action": m.one_of("approve_refund", "deny_refund", "escalate"),
            "reason": m.string(min_len=1),
            "ticket_id": m.optional(m.regex(r"^TICKET-\d+$")),
            "refund_amount": m.optional(m.number(min=0)),
        },
        rules=[
            m.require("ticket_id").when(m.field("action") == "escalate"),
            m.forbid("refund_amount").when(m.field("action") == "deny_refund"),
        ],
    ).where(lambda o: o["reason"] != "forbidden", "reason blocked")

    ok_escalate = {
        "action": "escalate",
        "reason": "needs human",
        "ticket_id": "TICKET-9",
    }
    assert m.check(spec, ok_escalate).ok

    missing_ticket = {
        "action": "escalate",
        "reason": "needs human",
    }
    r = m.check(spec, missing_ticket)
    assert not r.ok
    assert any(e.code == "conditional_rule" for e in r.errors)

    deny_with_refund = {
        "action": "deny_refund",
        "reason": "no",
        "refund_amount": 10,
    }
    r2 = m.check(spec, deny_with_refund)
    assert not r2.ok
    assert any(e.code == "conditional_rule" for e in r2.errors)

    r3 = m.check(spec, {**ok_escalate, "reason": "forbidden"})
    assert not r3.ok
    assert any(e.code == "where" for e in r3.errors)


def test_list_exact_unordered_of() -> None:
    assert m.check(m.list_exact(1, 2, 3), [1, 2, 3]).ok
    assert not m.check(m.list_exact(1, 2), [1, 2, 3]).ok

    u = m.list_unordered(1, 1, 2)
    assert m.check(u, [2, 1, 1]).ok
    assert not m.check(u, [1, 2, 2]).ok

    assert m.check(m.list_of(m.number(min=0)), [0, 2.5, 3]).ok
    assert not m.check(m.list_of(m.number(min=0)), [0, -1]).ok


def test_transform() -> None:
    spec = m.transform(lambda s: int(s), m.number(int_only=True))
    assert m.check(spec, "7").ok
    assert not m.check(spec, "nope").ok


def test_nested_json_fixture() -> None:
    """Deeply nested structure mixing objects, lists, multiset, rules, predicates."""

    spec = m.object(
        {
            "version": 1,
            "payload": {
                "users": m.list_of(
                    m.object(
                        {
                            "id": m.string(min_len=1),
                            "scores": m.list_unordered(
                                m.number(min=0),
                                m.number(min=0),
                                lambda x: x == 100,
                            ),
                            "meta": m.optional(
                                m.object(
                                    {
                                        "flag": True,
                                    },
                                    extra="forbid",
                                )
                            ),
                        },
                        extra="forbid",
                    )
                ),
                "tags": m.list_exact("alpha", "beta"),
            },
            "audit": m.list_of(
                m.object(
                    {
                        "kind": m.one_of("create", "update"),
                        "ref": lambda x: isinstance(x, str) and len(x) > 0,
                    }
                )
            ),
        },
        rules=[
            m.require("payload").when(m.field("version") == 1),
        ],
        extra="forbid",
    )

    actual = {
        "version": 1,
        "payload": {
            "users": [
                {
                    "id": "u1",
                    "scores": [100, 0, 50],
                    "meta": {"flag": True},
                },
                {
                    "id": "u2",
                    "scores": [50, 100, 0],
                },
            ],
            "tags": ["alpha", "beta"],
        },
        "audit": [
            {"kind": "create", "ref": "a1"},
            {"kind": "update", "ref": "a2"},
        ],
    }
    r = m.check(spec, actual)
    assert r.ok, r.errors

    bad_tags = {
        **actual,
        "payload": {
            **actual["payload"],
            "tags": ["beta", "alpha"],
        },
    }
    r2 = m.check(spec, bad_tags)
    assert not r2.ok
    assert r2.errors


def test_regex_pattern_coercion() -> None:
    pat = re.compile(r"^[a-z]+$")
    r = m.check(pat, "abc")
    assert r.ok
    assert not m.check(pat, "Abc").ok


def test_single_arg_match_returns_matcher() -> None:
    inner = m.match(3)
    assert m.check(inner, 3).ok


def test_typeerror_unknown_coercion() -> None:
    with pytest.raises(TypeError):
        m.match(object())  # noqa: B009 — builtin instance, not a matcher


def test_optional_key_missing_vs_none() -> None:
    spec = m.object({"x": m.optional(m.string())})
    assert m.check(spec, {}).ok
    assert m.check(spec, {"x": None}).ok
    assert m.check(spec, {"x": "a"}).ok


def test_field_compare_ops() -> None:
    spec = m.object(
        {
            "n": m.number(),
            "flag": m.optional(m.any_value()),
        },
        rules=[m.require("flag").when(m.field("n") > 5)],
    )
    assert not m.check(spec, {"n": 10}).ok
    assert m.check(spec, {"n": 10, "flag": True}).ok
    assert m.check(spec, {"n": 3}).ok


@dataclass
class _SampleDataclass:
    name: str
    count: int


@dataclass
class _InnerDc:
    x: int


@dataclass
class _OuterDc:
    inner: _InnerDc


def test_check_dataclass_instance_matches_object_spec() -> None:
    spec = m.object({"name": m.string(min_len=1), "count": 3})
    assert m.check(spec, _SampleDataclass(name="a", count=3)).ok
    r = m.check(spec, _SampleDataclass(name="", count=3))
    assert not r.ok
    assert any(e.path == ("name",) for e in r.errors)


def test_check_nested_dataclass_for_inner_object_spec() -> None:
    spec = m.object({"inner": m.object({"x": 1})})
    assert m.check(spec, _OuterDc(inner=_InnerDc(x=1))).ok
    r = m.check(spec, _OuterDc(inner=_InnerDc(x=2)))
    assert not r.ok
    assert any(e.path == ("inner", "x") for e in r.errors)


def test_check_pydantic_model_matches_object_spec() -> None:
    class _PM(BaseModel):
        name: str
        n: int

    spec = m.object({"name": "hi", "n": m.number(min=0)})
    assert m.check(spec, _PM(name="hi", n=0)).ok
    r = m.check(spec, _PM(name="hi", n=-1))
    assert not r.ok
    assert any(e.path == ("n",) for e in r.errors)


def test_check_pydantic_nested_models_in_object_spec() -> None:
    class _Inner(BaseModel):
        tag: str

    class _Outer(BaseModel):
        inner: _Inner

    spec = m.object({"inner": m.object({"tag": m.string(min_len=1)})})
    assert m.check(spec, _Outer(inner=_Inner(tag="ok"))).ok
    r = m.check(spec, _Outer(inner=_Inner(tag="")))
    assert not r.ok
    assert any(e.path == ("inner", "tag") for e in r.errors)


# --- Error paths, codes, and messages -------------------------------------------------


def test_error_root_equality_has_empty_path() -> None:
    r = m.check(1, 2)
    assert not r.ok
    assert len(r.errors) == 1
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "equality"
    assert "equal" in e.message.lower()
    assert e.expected == "1"
    assert e.actual == "2"


def test_error_nested_object_path() -> None:
    spec = m.object({"outer": m.object({"inner": 42})})
    r = m.check(spec, {"outer": {"inner": 0}})
    assert not r.ok
    assert len(r.errors) == 1
    e = r.errors[0]
    assert e.path == ("outer", "inner")
    assert e.code == "equality"


def test_error_list_exact_element_path() -> None:
    r = m.check(m.list_exact(1, 2, 3), [1, 9, 3])
    assert not r.ok
    assert len(r.errors) == 1
    e = r.errors[0]
    assert e.path == (1,)
    assert e.code == "equality"


def test_error_list_exact_length_message() -> None:
    r = m.check(m.list_exact(1, 2), [1])
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "list_exact"
    assert "length" in e.message.lower()


def test_error_missing_key_path_and_message() -> None:
    r = m.check(m.object({"a": 1, "b": 2}), {})
    assert not r.ok
    paths = {e.path for e in r.errors if e.code == "missing_key"}
    assert ("a",) in paths
    assert ("b",) in paths
    for e in r.errors:
        if e.code == "missing_key":
            assert "a" in e.message or "b" in e.message
            assert e.actual == "(absent)"


def test_error_extra_key_path() -> None:
    r = m.check(m.object({"a": 1}, extra="forbid"), {"a": 1, "oops": 99})
    assert not r.ok
    extra = [e for e in r.errors if e.code == "extra_key"]
    assert len(extra) == 1
    assert extra[0].path == ("oops",)
    assert "unexpected" in extra[0].message.lower()


def test_error_list_of_nested_field_path() -> None:
    spec = m.list_of(m.object({"id": m.string(min_len=2)}))
    r = m.check(spec, [{"id": "x"}, {"id": "ok"}])
    assert not r.ok
    bad = [e for e in r.errors if e.path == (0, "id")]
    assert len(bad) == 1
    assert bad[0].code == "string"
    assert "min_len" in bad[0].message.lower()


def test_error_predicate_custom_message_at_root() -> None:
    p = m.match(lambda _: False, message="custom failure")
    r = m.check(p, 123)
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "predicate"
    assert e.message == "custom failure"


def test_error_conditional_require_path() -> None:
    spec = m.object(
        {"action": "escalate", "reason": "x"},
        rules=[m.require("ticket_id").when(m.field("action") == "escalate")],
    )
    r = m.check(spec, {"action": "escalate", "reason": "x"})
    assert not r.ok
    cond = [e for e in r.errors if e.code == "conditional_rule"]
    assert len(cond) == 1
    assert cond[0].path == ("ticket_id",)
    assert "require" in cond[0].message.lower() or "ticket_id" in cond[0].message


def test_error_where_escape_hatch_path_at_object_root() -> None:
    spec = m.object({"a": 1}).where(lambda o: o["a"] == 2, "a must be 2")
    r = m.check(spec, {"a": 1})
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "where"
    assert e.message == "a must be 2"


def test_error_transform_preserves_inner_path_in_message() -> None:
    # Transform succeeds; inner matcher fails so we exercise inner code + message prefix.
    spec = m.transform(lambda s: int(s), m.number(min=10))
    r = m.check(spec, "3")
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "number"
    assert "after transform" in e.message.lower()


def test_error_transform_fn_raises_reports_transform_code() -> None:
    spec = m.transform(lambda s: int(s), m.number(int_only=True))
    r = m.check(spec, "not-int")
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "transform"
    assert "transform raised" in e.message.lower()


def test_error_list_unordered_no_assignment_path_is_list_root() -> None:
    """When multiset cannot be satisfied, failure is reported at the list path."""
    r = m.check(m.list_unordered(1, 1, 2), [1, 2, 3])
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "list_unordered"
    assert "multiset" in e.message.lower() or "assignment" in e.message.lower() or "match" in e.message.lower()
