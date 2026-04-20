"""Tests for m.list() (all mode/allow_extras combinations) and m.list_of()."""

from __future__ import annotations

import pytest

import agent_spec_kit.match as m


def test_ordered_exact_basic_and_length() -> None:
    assert m.check(m.list([1, 2, 3]), [1, 2, 3]).ok
    assert not m.check(m.list([1, 2]), [1, 2, 3]).ok


def test_unordered_exact_multiset() -> None:
    u = m.list([1, 1, 2], mode="unordered", allow_extras=False)
    assert m.check(u, [2, 1, 1]).ok
    assert not m.check(u, [1, 2, 2]).ok


def test_list_of_unchanged() -> None:
    assert m.check(m.list_of(m.number(min=0)), [0, 2.5, 3]).ok
    assert not m.check(m.list_of(m.number(min=0)), [0, -1]).ok


def test_ordered_with_extras_subsequence() -> None:
    spec = m.list([1, 3], allow_extras=True)
    assert m.check(spec, [0, 1, 2, 3, 4]).ok
    assert m.check(spec, [1, 3]).ok
    assert not m.check(spec, [3, 1]).ok  # wrong order


def test_ordered_with_extras_subsequence_impossible() -> None:
    r = m.check(m.list([1, 2, 3], allow_extras=True), [3, 1])
    assert not r.ok
    assert r.errors[0].code == "list"
    msg = r.errors[0].message.lower()
    assert "order" in msg and ("left to right" in msg or "expected value" in msg)


def test_unordered_with_extras_injective() -> None:
    spec = m.list([1, 2], mode="unordered", allow_extras=True)
    assert m.check(spec, [9, 1, 8, 2]).ok
    assert not m.check(spec, [1, 1, 1]).ok  # cannot match 1 and 2 to three 1s


def test_unordered_with_extras_too_few_actual() -> None:
    r = m.check(m.list([1, 2, 3], mode="unordered", allow_extras=True), [1, 2])
    assert not r.ok
    assert r.errors[0].code == "list"
    assert "at least" in r.errors[0].message.lower()


def test_unordered_contains_no_assignment_failure_message() -> None:
    r = m.check(m.list([1, 1, 2], mode="unordered", allow_extras=True), [2, 2, 2, 2])
    assert not r.ok
    assert r.errors[0].code == "list"
    msg = r.errors[0].message.lower()
    assert "different" in msg and ("order" in msg or "ignored" in msg)


def test_duplicates_ordered_exact() -> None:
    assert m.check(m.list([1, 1, 2]), [1, 1, 2]).ok
    assert not m.check(m.list([1, 1, 2]), [1, 2, 1]).ok


def test_empty_expected_ordered() -> None:
    assert m.check(m.list([]), []).ok
    assert not m.check(m.list([]), [1]).ok


def test_empty_expected_ordered_extras() -> None:
    assert m.check(m.list([], allow_extras=True), []).ok
    assert m.check(m.list([], allow_extras=True), [1, 2]).ok


def test_empty_expected_unordered() -> None:
    assert m.check(m.list([], mode="unordered"), []).ok
    assert not m.check(m.list([], mode="unordered"), [1]).ok


def test_empty_expected_unordered_extras() -> None:
    assert m.check(m.list([], mode="unordered", allow_extras=True), [1, 2]).ok


def test_non_list_actual_all_modes() -> None:
    for mode in ("ordered", "unordered"):
        for allow_extras in (False, True):
            r = m.check(m.list([1], mode=mode, allow_extras=allow_extras), "nope")
            assert not r.ok
            assert r.errors[0].code == "list"
            assert "list" in r.errors[0].message.lower()


def test_coerce_literal_list_still_ordered_exact() -> None:
    """List literals in specs coerce to ordered exact-length list matcher."""
    assert m.check({"x": [1, 2]}, {"x": [1, 2]}).ok
    assert not m.check({"x": [1, 2]}, {"x": [1, 2, 3]}).ok


def test_unordered_exact_length_mismatch_message() -> None:
    r = m.check(m.list([1], mode="unordered", allow_extras=False), [1, 1])
    assert not r.ok
    assert r.errors[0].code == "list"
    msg = r.errors[0].message.lower()
    assert "length" in msg and "order" in msg


def test_list_rejects_str_as_elements() -> None:
    with pytest.raises(TypeError, match="str/bytes"):
        m.list("ab")  # type: ignore[arg-type]

