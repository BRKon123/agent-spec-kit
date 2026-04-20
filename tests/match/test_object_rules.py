"""Tests for object(), rules, field(), optional keys."""

from __future__ import annotations

import agent_spec_kit.match as m


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
