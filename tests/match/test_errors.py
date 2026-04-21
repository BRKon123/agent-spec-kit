"""Error paths, codes, and messages."""

from __future__ import annotations

import agent_spec_kit.match as m


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


def test_error_list_ordered_exact_element_path() -> None:
    r = m.check(m.list([1, 2, 3]), [1, 9, 3])
    assert not r.ok
    assert len(r.errors) == 1
    e = r.errors[0]
    assert e.path == (1,)
    assert e.code == "equality"


def test_error_list_ordered_exact_length_message() -> None:
    r = m.check(m.list([1, 2]), [1])
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "list_length_mismatch"
    em = e.message.lower()
    assert "length" in em or "wrong" in em
    assert "order" in em


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


def test_error_list_unordered_exact_no_assignment_path_is_list_root() -> None:
    """When multiset cannot be satisfied, failure is reported at the list path."""
    r = m.check(m.list([1, 1, 2], mode="unordered", allow_extras=False), [1, 2, 3])
    assert not r.ok
    e = r.errors[0]
    assert e.path == ()
    assert e.code == "unordered_mismatch"
    em = e.message.lower()
    assert "order" in em and ("ignored" in em or "different" in em or "position" in em)
