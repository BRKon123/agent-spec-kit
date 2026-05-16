"""Tests for m.object matching JSON object strings (e.g. tool results)."""

from __future__ import annotations

import agent_spec_kit.match as m


def test_object_matches_json_object_string() -> None:
    spec = m.object({"eligible": True, "reason_code": m.string(min_len=1)})
    assert m.check(spec, '{"eligible": true, "reason_code": "duplicate_charge"}').ok


def test_object_json_string_with_rules() -> None:
    spec = m.object(
        {
            "severity": m.one_of("low", "medium", "high"),
            "escalation_reason": m.optional(m.string(min_len=1)),
        },
        rules=[
            m.require("escalation_reason").when(m.field("severity") == "high"),
        ],
    )
    assert m.check(spec, '{"severity": "high", "escalation_reason": "outage"}').ok
    assert not m.check(spec, '{"severity": "high"}').ok


def test_object_rejects_invalid_json_string() -> None:
    spec = m.object({"a": 1})
    r = m.check(spec, "not json")
    assert not r.ok
    assert any(e.code == "object" for e in r.errors)


def test_object_rejects_json_array_string() -> None:
    spec = m.object({"a": 1})
    r = m.check(spec, "[1, 2, 3]")
    assert not r.ok
    assert any(e.code == "object" for e in r.errors)


def test_object_rejects_malformed_json_object_string() -> None:
    spec = m.object({"a": 1})
    r = m.check(spec, "{not valid}")
    assert not r.ok
    assert any(e.code == "object" for e in r.errors)
