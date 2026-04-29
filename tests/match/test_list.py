"""Tests for m.list() (all mode/allow_extras combinations) and m.list_of()."""

from __future__ import annotations

import asyncio
import json

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
    assert r.errors[0].code == "missing_element"
    msg = r.errors[0].message.lower()
    assert "order" in msg and ("expected element" in msg or "searched actual positions" in msg)


def test_unordered_with_extras_injective() -> None:
    spec = m.list([1, 2], mode="unordered", allow_extras=True)
    assert m.check(spec, [9, 1, 8, 2]).ok
    assert not m.check(spec, [1, 1, 1]).ok  # cannot match 1 and 2 to three 1s


def test_unordered_with_extras_too_few_actual() -> None:
    r = m.check(m.list([1, 2, 3], mode="unordered", allow_extras=True), [1, 2])
    assert not r.ok
    assert r.errors[0].code == "list_too_short"
    assert "at least" in r.errors[0].message.lower()


def test_unordered_contains_no_assignment_failure_message() -> None:
    r = m.check(m.list([1, 1, 2], mode="unordered", allow_extras=True), [2, 2, 2, 2])
    assert not r.ok
    assert r.errors[0].code == "unordered_mismatch"
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
    assert r.errors[0].code == "list_length_mismatch"
    msg = r.errors[0].message.lower()
    assert "length" in msg and "order" in msg


def test_list_rejects_str_as_elements() -> None:
    with pytest.raises(TypeError, match="str/bytes"):
        m.list("ab")  # type: ignore[arg-type]


def _tool_name(name: str):
    return m.object({"name": name})


def test_ordered_exact_failure_surfaces_outer_and_inner() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="ordered", allow_extras=False)
    actual = [{"name": "search"}, {"name": "read"}]
    r = m.check(spec, actual)
    assert not r.ok
    assert r.errors[0].code == "ordered_element_mismatch"
    assert "index 1" in r.errors[0].message
    assert "representative mismatch at expected index 1" in r.errors[0].message
    assert len(r.errors) >= 2
    assert any("write" in e.message or "write" in str(e.expected) for e in r.errors[1:])
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "ordered_exact"
    assert witness["first_failed_index"] == 1
    assert "inner_error" in witness


def test_ordered_subsequence_missing_expected_reports_attempts_and_inner() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="ordered", allow_extras=True)
    actual = [{"name": "search"}, {"name": "read"}, {"name": "delete"}]
    r = m.check(spec, actual)
    assert not r.ok
    assert r.errors[0].code == "missing_element"
    assert "expected element at index 1" in r.errors[0].message
    assert "searched actual positions" in r.errors[0].message
    assert "closest underlying mismatch" in r.errors[0].message
    assert len(r.errors) == 2
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "ordered_subsequence"
    assert witness["expected_index"] == 1
    assert witness["searched_actual_positions"] == [1, 2]
    assert "inner_error" in witness


def test_unordered_exact_permutation_failure_has_representative_comparison() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="unordered", allow_extras=False)
    actual = [{"name": "search"}, {"name": "read"}]
    r = m.check(spec, actual)
    assert not r.ok
    assert r.errors[0].code == "unordered_mismatch"
    assert "representative failed comparison" in r.errors[0].message
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "unordered_permutation"
    rep = witness["representative_failed_comparison"]
    assert isinstance(rep["expected_index"], int)
    assert isinstance(rep["actual_index"], int)
    assert "inner_error" in rep
    assert len(r.errors) == 2


def test_unordered_allow_extras_dfs_failure_has_representative_comparison() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="unordered", allow_extras=True)
    actual = [{"name": "search"}, {"name": "read"}, {"name": "delete"}]
    r = m.check(spec, actual)
    assert not r.ok
    assert r.errors[0].code == "unordered_mismatch"
    msg = r.errors[0].message.lower()
    assert "extras" in msg or "order does not matter" in msg
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "unordered_injective"
    assert witness["allow_extras"] is True
    assert "representative_failed_comparison" in witness


def test_unordered_exact_large_n_uses_injective_witness() -> None:
    expected_names = [f"tool_{i}" for i in range(10)]
    spec = m.list([_tool_name(name) for name in expected_names], mode="unordered", allow_extras=False)
    actual = [{"name": name} for name in expected_names]
    actual[-1] = {"name": "mismatch"}
    r = m.check(spec, actual)
    assert not r.ok
    assert r.errors[0].code == "unordered_mismatch"
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "unordered_injective"
    assert witness["allow_extras"] is False
    assert "representative_failed_comparison" in witness


def test_ordered_exact_length_mismatch_witness_unchanged() -> None:
    r = m.check(m.list([1, 2], mode="ordered", allow_extras=False), [1])
    assert not r.ok
    assert r.errors[0].code == "list_length_mismatch"
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["expected_len"] == 2
    assert witness["actual_len"] == 1
    assert "inner_error" not in witness


def test_list_of_failure_adds_outer_error_and_preserves_inner() -> None:
    r = m.check(m.list_of(_tool_name("search")), [{"name": "search"}, {"name": "read"}])
    assert not r.ok
    assert r.errors[0].code == "list_of_element_mismatch"
    assert "index 1" in r.errors[0].message
    assert "representative mismatch at index 1" in r.errors[0].message
    assert len(r.errors) >= 2
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "list_of"
    assert witness["first_failed_index"] == 1
    assert "inner_error" in witness


def test_async_ordered_exact_failure_parity() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="ordered", allow_extras=False)
    actual = [{"name": "search"}, {"name": "read"}]
    r = asyncio.run(m.async_check(spec, actual))
    assert not r.ok
    assert r.errors[0].code == "ordered_element_mismatch"
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "ordered_exact"
    assert witness["first_failed_index"] == 1


def test_async_ordered_subsequence_failure_parity() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="ordered", allow_extras=True)
    actual = [{"name": "search"}, {"name": "read"}, {"name": "delete"}]
    r = asyncio.run(m.async_check(spec, actual))
    assert not r.ok
    assert r.errors[0].code == "missing_element"
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "ordered_subsequence"
    assert witness["expected_index"] == 1
    assert witness["searched_actual_positions"] == [1, 2]


def test_async_unordered_permutation_failure_parity() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="unordered", allow_extras=False)
    actual = [{"name": "search"}, {"name": "read"}]
    r = asyncio.run(m.async_check(spec, actual))
    assert not r.ok
    assert r.errors[0].code == "unordered_mismatch"
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "unordered_permutation"
    assert "representative_failed_comparison" in witness


def test_async_unordered_injective_failure_parity() -> None:
    spec = m.list([_tool_name("search"), _tool_name("write")], mode="unordered", allow_extras=True)
    actual = [{"name": "search"}, {"name": "read"}, {"name": "delete"}]
    r = asyncio.run(m.async_check(spec, actual))
    assert not r.ok
    assert r.errors[0].code == "unordered_mismatch"
    witness = json.loads(r.errors[0].witness_json or "{}")
    assert witness["mode"] == "unordered_injective"
    assert witness["allow_extras"] is True
    assert "representative_failed_comparison" in witness

