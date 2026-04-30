"""List matchers: ordered/unordered with optional extras, homogeneous list_of."""

from __future__ import annotations

import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr, path_to_str

_MAX_PERM = 9  # exhaustive permutation search for multiset (factorial growth)


def _path_depth(error: MatchError) -> int:
    return len(error.path)


def _pick_representative_error(errors: list[MatchError]) -> MatchError | None:
    """
    Pick the most useful inner matcher error to surface.

    Prefer deeper paths because they usually point to the precise nested mismatch,
    e.g. path=(2, "arguments", "query") is more useful than path=(2,).
    """
    if not errors:
        return None
    return max(errors, key=_path_depth)


def _error_payload(error: MatchError) -> dict[str, Any]:
    return {
        "path": list(error.path),
        "code": error.code,
        "message": error.message,
        "expected": error.expected,
        "actual": error.actual,
        "witness_json": error.witness_json,
    }


def _with_inner_error(outer: MatchError, inner: MatchError | None) -> MatchResult:
    if inner is None:
        return MatchResult.failure(outer)
    return MatchResult(ok=False, errors=(outer, inner))


@dataclass(frozen=True, slots=True)
class _ComparisonFailure:
    expected_index: int
    actual_index: int
    errors: tuple[MatchError, ...]


def _pick_representative_comparison(
    failures: list[_ComparisonFailure],
) -> tuple[_ComparisonFailure, MatchError] | None:
    """
    Pick the most useful failed expected/actual comparison.

    This is used by unordered matchers, where many possible pairings are tried.
    The returned comparison is a debugging hint, not necessarily a complete proof
    of why the global assignment failed.
    """
    best_failure: _ComparisonFailure | None = None
    best_error: MatchError | None = None

    for failure in failures:
        candidate = _pick_representative_error(list(failure.errors))
        if candidate is None:
            continue

        if best_error is None or _path_depth(candidate) > _path_depth(best_error):
            best_failure = failure
            best_error = candidate

    if best_failure is None or best_error is None:
        return None

    return best_failure, best_error


def _actual_tool_names_from_list(actual: list[Any]) -> list[str]:
    names: list[str] = []
    for item in actual:
        if isinstance(item, dict) and "name" in item:
            names.append(str(item["name"]))
        else:
            names.append(type(item).__name__)
    return names


def _expected_tool_names_from_elements(elements: tuple[BaseMatcher, ...]) -> list[str] | None:
    """If each element is an object matcher with a string equality on ``name``, return names."""
    from agent_spec_kit.match.object import ObjectMatcher
    from agent_spec_kit.match.scalars import EqualityMatcher

    out: list[str] = []
    for em in elements:
        if isinstance(em, ObjectMatcher) and "name" in em.props:
            nm = em.props["name"]
            if isinstance(nm, EqualityMatcher) and isinstance(nm.expected, str):
                out.append(nm.expected)
                continue
        return None
    return out


def _list_length_witness_payload(
    *,
    mode: str,
    elements: tuple[BaseMatcher, ...],
    actual: list[Any],
    expected_len: int,
    actual_len: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": mode,
        "expected_len": expected_len,
        "actual_len": actual_len,
        "actual_witness": actual[: min(8, len(actual))],
    }
    if extra:
        payload.update(extra)
    exp_names = _expected_tool_names_from_elements(elements)
    act_names = _actual_tool_names_from_list(actual)
    if exp_names is not None and len(exp_names) == expected_len:
        payload["expected_tool_names"] = exp_names
        payload["actual_tool_names"] = act_names
    return payload


def _not_list_error(path: Path, actual: Any) -> MatchResult:
    return MatchResult.failure(
        MatchError(
            path=path,
            code="list",
            message="expected a list",
            expected="list",
            actual=type(actual).__name__,
        )
    )


def _ordered_exact(
    elements: tuple[BaseMatcher, ...], actual: list[Any], path: Path
) -> MatchResult:
    if len(actual) != len(elements):
        witness = _list_length_witness_payload(
            mode="ordered_exact",
            elements=elements,
            actual=actual,
            expected_len=len(elements),
            actual_len=len(actual),
        )
        return MatchResult.failure(
            MatchError(
                path=path,
                code="list_length_mismatch",
                message=(
                    "wrong list length: expected exactly "
                    f"{len(elements)} value(s) in this order, found {len(actual)}"
                ),
                expected=str(len(elements)),
                actual=str(len(actual)),
                witness_json=json.dumps(witness, default=str),
            )
        )
    errors: list[MatchError] = []
    first_failed_index: int | None = None
    first_failed_inner: MatchError | None = None
    for i, (em, val) in enumerate(zip(elements, actual, strict=True)):
        r = em.check(val, path + (i,))
        if not r.ok:
            errors.extend(r.errors)
            if first_failed_index is None:
                first_failed_index = i
                first_failed_inner = _pick_representative_error(list(r.errors))
    if errors:
        witness: dict[str, Any] = {
            "mode": "ordered_exact",
            "first_failed_index": first_failed_index,
            "actual_witness": actual[:12],
        }
        if first_failed_inner is not None:
            witness["inner_error"] = _error_payload(first_failed_inner)

        outer = MatchError(
            path=path if first_failed_index is None else path + (first_failed_index,),
            code="ordered_element_mismatch",
            message=(
                f"list item at index {first_failed_index} did not match the expected matcher for that position"
                if first_failed_index is not None
                else "one or more list items did not match their expected positions"
            ),
            expected="each list item to match the expected matcher at the same index",
            actual=_short_repr(actual),
            witness_json=json.dumps(witness, default=str),
        )
        if first_failed_inner is not None and first_failed_index is not None:
            outer = MatchError(
                path=outer.path,
                code=outer.code,
                message=(
                    f"{outer.message}; representative mismatch at expected index {first_failed_index} "
                    f"(actual index {first_failed_index}): {first_failed_inner.message}"
                ),
                expected=outer.expected,
                actual=outer.actual,
                witness_json=outer.witness_json,
            )
        return MatchResult(ok=False, errors=(outer, *tuple(errors)))
    return MatchResult.success()


async def _ordered_exact_async(
    elements: tuple[BaseMatcher, ...], actual: list[Any], path: Path
) -> MatchResult:
    if len(actual) != len(elements):
        witness = _list_length_witness_payload(
            mode="ordered_exact",
            elements=elements,
            actual=actual,
            expected_len=len(elements),
            actual_len=len(actual),
        )
        return MatchResult.failure(
            MatchError(
                path=path,
                code="list_length_mismatch",
                message=(
                    "wrong list length: expected exactly "
                    f"{len(elements)} value(s) in this order, found {len(actual)}"
                ),
                expected=str(len(elements)),
                actual=str(len(actual)),
                witness_json=json.dumps(witness, default=str),
            )
        )
    errors: list[MatchError] = []
    first_failed_index: int | None = None
    first_failed_inner: MatchError | None = None
    for i, (em, val) in enumerate(zip(elements, actual, strict=True)):
        r = await em.async_check(val, path + (i,))
        if not r.ok:
            errors.extend(r.errors)
            if first_failed_index is None:
                first_failed_index = i
                first_failed_inner = _pick_representative_error(list(r.errors))
    if errors:
        witness: dict[str, Any] = {
            "mode": "ordered_exact",
            "first_failed_index": first_failed_index,
            "actual_witness": actual[:12],
        }
        if first_failed_inner is not None:
            witness["inner_error"] = _error_payload(first_failed_inner)

        outer = MatchError(
            path=path if first_failed_index is None else path + (first_failed_index,),
            code="ordered_element_mismatch",
            message=(
                f"list item at index {first_failed_index} did not match the expected matcher for that position"
                if first_failed_index is not None
                else "one or more list items did not match their expected positions"
            ),
            expected="each list item to match the expected matcher at the same index",
            actual=_short_repr(actual),
            witness_json=json.dumps(witness, default=str),
        )
        if first_failed_inner is not None and first_failed_index is not None:
            outer = MatchError(
                path=outer.path,
                code=outer.code,
                message=(
                    f"{outer.message}; representative mismatch at expected index {first_failed_index} "
                    f"(actual index {first_failed_index}): {first_failed_inner.message}"
                ),
                expected=outer.expected,
                actual=outer.actual,
                witness_json=outer.witness_json,
            )
        return MatchResult(ok=False, errors=(outer, *tuple(errors)))
    return MatchResult.success()


def _ordered_subsequence(
    elements: tuple[BaseMatcher, ...], actual: list[Any], path: Path
) -> MatchResult:
    # This preserves the current greedy subsequence semantics. The first expected
    # matcher that cannot be placed is reported as the list-level failure, and the
    # closest/deepest inner matcher error from the attempted placements is attached.
    ai = 0
    for expected_index, em in enumerate(elements):
        tried_errors: list[MatchError] = []
        tried_positions: list[int] = []
        while ai < len(actual):
            actual_index = ai
            r = em.check(actual[actual_index], path + (actual_index,))
            if r.ok:
                ai += 1
                break
            tried_positions.append(actual_index)
            tried_errors.extend(r.errors)
            ai += 1
        else:
            inner = _pick_representative_error(tried_errors)
            witness: dict[str, Any] = {
                "mode": "ordered_subsequence",
                "expected_index": expected_index,
                "searched_actual_positions": tried_positions,
                "actual_witness": actual[:12],
            }
            if inner is not None:
                witness["inner_error"] = _error_payload(inner)

            message = (
                f"could not match expected element at index {expected_index} while preserving order"
            )
            if tried_positions:
                message += (
                    f"\nsearched actual positions {tried_positions[0]} through {tried_positions[-1]}"
                )
            else:
                message += (
                    f"\nno actual items were left to search"
                )
            if inner is not None:
                message += (
                    f"\nclosest underlying mismatch was (at {path_to_str(inner.path)}): "
                    f"{inner.message}"
                )

            outer = MatchError(
                path=path + (expected_index,),
                code="missing_element",
                message=message,
                expected="expected value to appear after the previous match",
                actual=_short_repr(actual),
                witness_json=json.dumps(witness, default=str),
            )
            return _with_inner_error(outer, inner)
    return MatchResult.success()


async def _ordered_subsequence_async(
    elements: tuple[BaseMatcher, ...], actual: list[Any], path: Path
) -> MatchResult:
    # This preserves the current greedy subsequence semantics. The first expected
    # matcher that cannot be placed is reported as the list-level failure, and the
    # closest/deepest inner matcher error from the attempted placements is attached.
    ai = 0
    for expected_index, em in enumerate(elements):
        tried_errors: list[MatchError] = []
        tried_positions: list[int] = []
        while ai < len(actual):
            actual_index = ai
            r = await em.async_check(actual[actual_index], path + (actual_index,))
            if r.ok:
                ai += 1
                break
            tried_positions.append(actual_index)
            tried_errors.extend(r.errors)
            ai += 1
        else:
            inner = _pick_representative_error(tried_errors)
            witness: dict[str, Any] = {
                "mode": "ordered_subsequence",
                "expected_index": expected_index,
                "searched_actual_positions": tried_positions,
                "actual_witness": actual[:12],
            }
            if inner is not None:
                witness["inner_error"] = _error_payload(inner)

            message = (
                f"could not match expected element at index {expected_index} while preserving order"
            )
            if tried_positions:
                message += (
                    f"\nsearched actual positions {tried_positions[0]} through {tried_positions[-1]}"
                )
            else:
                message += "\nno actual items were left to search"
            if inner is not None:
                message += (
                    f"\nclosest underlying mismatch was (at {path_to_str(inner.path)}): "
                    f"{inner.message}"
                )

            outer = MatchError(
                path=path + (expected_index,),
                code="missing_element",
                message=message,
                expected="expected value to appear after the previous match",
                actual=_short_repr(actual),
                witness_json=json.dumps(witness, default=str),
            )
            return _with_inner_error(outer, inner)
    return MatchResult.success()


def _multiset_by_permutation(
    specs: list[BaseMatcher], actual: list[Any], path: Path
) -> MatchResult:
    n = len(specs)
    failures: list[_ComparisonFailure] = []
    for perm in itertools.permutations(range(n)):
        for expected_index, actual_index in enumerate(perm):
            r = specs[expected_index].check(actual[actual_index], path + (actual_index,))
            if not r.ok:
                failures.append(
                    _ComparisonFailure(
                        expected_index=expected_index,
                        actual_index=actual_index,
                        errors=tuple(r.errors),
                    )
                )
                break
        else:
            return MatchResult.success()
    picked = _pick_representative_comparison(failures)
    witness: dict[str, Any] = {
        "mode": "unordered_permutation",
        "actual_witness": actual[:12],
    }
    inner: MatchError | None = None
    message = (
        "the list does not match when order is ignored: each expected value "
        "must correspond to a different position in the list"
    )
    if picked is not None:
        failure, inner = picked
        witness["representative_failed_comparison"] = {
            "expected_index": failure.expected_index,
            "actual_index": failure.actual_index,
            "inner_error": _error_payload(inner),
        }
        message += (
            f"; representative failed comparison was expected element "
            f"{failure.expected_index} against actual item {failure.actual_index}: "
            f"{inner.message}"
        )

    outer = MatchError(
        path=path,
        code="unordered_mismatch",
        message=message,
        expected="each value matched to a different position (order ignored)",
        actual=_short_repr(actual),
        witness_json=json.dumps(witness, default=str),
    )
    return _with_inner_error(outer, inner)


async def _multiset_by_permutation_async(
    specs: list[BaseMatcher], actual: list[Any], path: Path
) -> MatchResult:
    n = len(specs)
    failures: list[_ComparisonFailure] = []
    for perm in itertools.permutations(range(n)):
        for expected_index, actual_index in enumerate(perm):
            r = await specs[expected_index].async_check(actual[actual_index], path + (actual_index,))
            if not r.ok:
                failures.append(
                    _ComparisonFailure(
                        expected_index=expected_index,
                        actual_index=actual_index,
                        errors=tuple(r.errors),
                    )
                )
                break
        else:
            return MatchResult.success()
    picked = _pick_representative_comparison(failures)
    witness: dict[str, Any] = {
        "mode": "unordered_permutation",
        "actual_witness": actual[:12],
    }
    inner: MatchError | None = None
    message = (
        "the list does not match when order is ignored: each expected value "
        "must correspond to a different position in the list"
    )
    if picked is not None:
        failure, inner = picked
        witness["representative_failed_comparison"] = {
            "expected_index": failure.expected_index,
            "actual_index": failure.actual_index,
            "inner_error": _error_payload(inner),
        }
        message += (
            f"; representative failed comparison was expected element "
            f"{failure.expected_index} against actual item {failure.actual_index}: "
            f"{inner.message}"
        )

    outer = MatchError(
        path=path,
        code="unordered_mismatch",
        message=message,
        expected="each value matched to a different position (order ignored)",
        actual=_short_repr(actual),
        witness_json=json.dumps(witness, default=str),
    )
    return _with_inner_error(outer, inner)


def _unordered_injective_dfs(
    specs: list[BaseMatcher], actual: list[Any], path: Path, *, allow_extras: bool
) -> MatchResult:
    n = len(specs)
    m = len(actual)
    used = [False] * m
    failures: list[_ComparisonFailure] = []

    def dfs(i: int) -> bool:
        if i == n:
            return True
        for j in range(m):
            if used[j]:
                continue
            r = specs[i].check(actual[j], path + (j,))
            if not r.ok:
                failures.append(
                    _ComparisonFailure(
                        expected_index=i,
                        actual_index=j,
                        errors=tuple(r.errors),
                    )
                )
                continue
            used[j] = True
            if dfs(i + 1):
                return True
            used[j] = False
        return False

    if dfs(0):
        return MatchResult.success()
    # In unordered matching, a representative failed comparison is only a debugging
    # hint. The actual failure is global: no complete injective assignment exists.
    # We surface the deepest inner error encountered because it is usually the most
    # actionable mismatch for the user.
    picked = _pick_representative_comparison(failures)
    if allow_extras:
        msg = (
            "could not match each expected value to a different item in the list "
            "(order does not matter; extra items in the list are allowed)"
        )
    else:
        msg = (
            "the list does not match when order is ignored: each expected value "
            "must correspond to a different position in the list"
        )
    witness: dict[str, Any] = {
        "mode": "unordered_injective",
        "allow_extras": allow_extras,
        "actual_witness": actual[:12],
    }
    inner: MatchError | None = None
    if picked is not None:
        failure, inner = picked
        witness["representative_failed_comparison"] = {
            "expected_index": failure.expected_index,
            "actual_index": failure.actual_index,
            "inner_error": _error_payload(inner),
        }
        msg += (
            f"; representative failed comparison was expected element "
            f"{failure.expected_index} against actual item {failure.actual_index}: "
            f"{inner.message}"
        )

    outer = MatchError(
        path=path,
        code="unordered_mismatch",
        message=msg,
        expected=(
            "each value to a different item (order ignored, extras allowed)"
            if allow_extras
            else "each value to a different position (order ignored)"
        ),
        actual=_short_repr(actual),
        witness_json=json.dumps(witness, default=str),
    )
    return _with_inner_error(outer, inner)


async def _unordered_injective_dfs_async(
    specs: list[BaseMatcher], actual: list[Any], path: Path, *, allow_extras: bool
) -> MatchResult:
    n = len(specs)
    m = len(actual)
    used = [False] * m
    failures: list[_ComparisonFailure] = []

    async def dfs(i: int) -> bool:
        if i == n:
            return True
        for j in range(m):
            if used[j]:
                continue
            r = await specs[i].async_check(actual[j], path + (j,))
            if not r.ok:
                failures.append(
                    _ComparisonFailure(
                        expected_index=i,
                        actual_index=j,
                        errors=tuple(r.errors),
                    )
                )
                continue
            used[j] = True
            if await dfs(i + 1):
                return True
            used[j] = False
        return False

    if await dfs(0):
        return MatchResult.success()
    # In unordered matching, a representative failed comparison is only a debugging
    # hint. The actual failure is global: no complete injective assignment exists.
    # We surface the deepest inner error encountered because it is usually the most
    # actionable mismatch for the user.
    picked = _pick_representative_comparison(failures)
    if allow_extras:
        msg = (
            "could not match each expected value to a different item in the list "
            "(order does not matter; extra items in the list are allowed)"
        )
    else:
        msg = (
            "the list does not match when order is ignored: each expected value "
            "must correspond to a different position in the list"
        )
    witness: dict[str, Any] = {
        "mode": "unordered_injective",
        "allow_extras": allow_extras,
        "actual_witness": actual[:12],
    }
    inner: MatchError | None = None
    if picked is not None:
        failure, inner = picked
        witness["representative_failed_comparison"] = {
            "expected_index": failure.expected_index,
            "actual_index": failure.actual_index,
            "inner_error": _error_payload(inner),
        }
        msg += (
            f"; representative failed comparison was expected element "
            f"{failure.expected_index} against actual item {failure.actual_index}: "
            f"{inner.message}"
        )

    outer = MatchError(
        path=path,
        code="unordered_mismatch",
        message=msg,
        expected=(
            "each value to a different item (order ignored, extras allowed)"
            if allow_extras
            else "each value to a different position (order ignored)"
        ),
        actual=_short_repr(actual),
        witness_json=json.dumps(witness, default=str),
    )
    return _with_inner_error(outer, inner)


@dataclass(frozen=True, slots=True)
class ListMatcher(BaseMatcher):
    """
    Match lists with optional order and whether extra items in the actual list are allowed.

    - ``mode="ordered"``, ``allow_extras=False``: same length; each position must match.
    - ``mode="ordered"``, ``allow_extras=True``: each expected value must appear in order
      from left to right (other values may appear in between).
    - ``mode="unordered"``, ``allow_extras=False``: same length; order can differ; each
      expected value must match a different item in the list.
    - ``mode="unordered"``, ``allow_extras=True``: same as above, but the list may be
      longer; extra items are ignored.
    """

    elements: tuple[BaseMatcher, ...]
    mode: Literal["ordered", "unordered"]
    allow_extras: bool

    def check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, list):
            return _not_list_error(path, actual)

        if self.mode == "ordered":
            if not self.allow_extras:
                return _ordered_exact(self.elements, actual, path)
            return _ordered_subsequence(self.elements, actual, path)

        n = len(self.elements)
        m = len(actual)
        specs = list(self.elements)

        if not self.allow_extras:
            if m != n:
                witness = _list_length_witness_payload(
                    mode="unordered_exact",
                    elements=self.elements,
                    actual=actual,
                    expected_len=n,
                    actual_len=m,
                )
                return MatchResult.failure(
                    MatchError(
                        path=path,
                        code="list_length_mismatch",
                        message=(
                            "wrong list length: expected exactly "
                            f"{n} value(s) when order is ignored, found {m}"
                        ),
                        expected=str(n),
                        actual=str(m),
                        witness_json=json.dumps(witness, default=str),
                    )
                )
            if n == 0:
                return MatchResult.success()
            if n <= _MAX_PERM:
                return _multiset_by_permutation(specs, actual, path)
            return _unordered_injective_dfs(specs, actual, path, allow_extras=False)

        if m < n:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_too_short",
                    message=(
                        "list is too short: need at least "
                        f"{n} item(s) to match all expected values (order does not matter)"
                    ),
                    expected=f">= {n}",
                    actual=str(m),
                    witness_json=json.dumps(
                        {"expected_min": n, "actual_len": m, "actual_witness": actual},
                        default=str,
                    ),
                )
            )
        if n == 0:
            return MatchResult.success()
        return _unordered_injective_dfs(specs, actual, path, allow_extras=True)

    async def async_check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, list):
            return _not_list_error(path, actual)

        if self.mode == "ordered":
            if not self.allow_extras:
                return await _ordered_exact_async(self.elements, actual, path)
            return await _ordered_subsequence_async(self.elements, actual, path)

        n = len(self.elements)
        m = len(actual)
        specs = list(self.elements)

        if not self.allow_extras:
            if m != n:
                witness = _list_length_witness_payload(
                    mode="unordered_exact",
                    elements=self.elements,
                    actual=actual,
                    expected_len=n,
                    actual_len=m,
                )
                return MatchResult.failure(
                    MatchError(
                        path=path,
                        code="list_length_mismatch",
                        message=(
                            "wrong list length: expected exactly "
                            f"{n} value(s) when order is ignored, found {m}"
                        ),
                        expected=str(n),
                        actual=str(m),
                        witness_json=json.dumps(witness, default=str),
                    )
                )
            if n == 0:
                return MatchResult.success()
            if n <= _MAX_PERM:
                return await _multiset_by_permutation_async(specs, actual, path)
            return await _unordered_injective_dfs_async(specs, actual, path, allow_extras=False)

        if m < n:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_too_short",
                    message=(
                        "list is too short: need at least "
                        f"{n} item(s) to match all expected values (order does not matter)"
                    ),
                    expected=f">= {n}",
                    actual=str(m),
                    witness_json=json.dumps(
                        {"expected_min": n, "actual_len": m, "actual_witness": actual},
                        default=str,
                    ),
                )
            )
        if n == 0:
            return MatchResult.success()
        return await _unordered_injective_dfs_async(specs, actual, path, allow_extras=True)


def list_matcher(
    elements: Sequence[Any],
    *,
    mode: Literal["ordered", "unordered"] = "ordered",
    allow_extras: bool = False,
) -> ListMatcher:
    if isinstance(elements, (str, bytes, bytearray)):
        raise TypeError(
            "list_matcher() expects a list or tuple of specs, not str/bytes "
            "(use a list/tuple of specs, e.g. m.list([spec1, spec2]))"
        )
    return ListMatcher(
        elements=tuple(coerce_any(e) for e in elements),
        mode=mode,
        allow_extras=allow_extras,
    )


@dataclass(frozen=True, slots=True)
class ListOfMatcher(BaseMatcher):
    inner: BaseMatcher

    def check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, list):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_of",
                    message="expected a list",
                    expected="list",
                    actual=type(actual).__name__,
                )
            )
        errors: list[MatchError] = []
        first_failed_index: int | None = None
        first_failed_inner: MatchError | None = None
        for i, val in enumerate(actual):
            r = self.inner.check(val, path + (i,))
            if not r.ok:
                errors.extend(r.errors)
                if first_failed_index is None:
                    first_failed_index = i
                    first_failed_inner = _pick_representative_error(list(r.errors))
        if errors:
            witness: dict[str, Any] = {
                "mode": "list_of",
                "first_failed_index": first_failed_index,
                "actual_witness": actual[:12],
            }
            if first_failed_inner is not None:
                witness["inner_error"] = _error_payload(first_failed_inner)
            outer = MatchError(
                path=path if first_failed_index is None else path + (first_failed_index,),
                code="list_of_element_mismatch",
                message=(
                    f"list item at index {first_failed_index} did not match the list_of matcher"
                    if first_failed_index is not None
                    else "one or more list items did not match the list_of matcher"
                ),
                expected="every list item to match the inner matcher",
                actual=_short_repr(actual),
                witness_json=json.dumps(witness, default=str),
            )
            if first_failed_inner is not None and first_failed_index is not None:
                outer = MatchError(
                    path=outer.path,
                    code=outer.code,
                    message=(
                        f"{outer.message}; representative mismatch at index {first_failed_index}: "
                        f"{first_failed_inner.message}"
                    ),
                    expected=outer.expected,
                    actual=outer.actual,
                    witness_json=outer.witness_json,
                )
            return MatchResult(ok=False, errors=(outer, *tuple(errors)))
        return MatchResult.success()

    async def async_check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, list):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_of",
                    message="expected a list",
                    expected="list",
                    actual=type(actual).__name__,
                )
            )
        errors: list[MatchError] = []
        first_failed_index: int | None = None
        first_failed_inner: MatchError | None = None
        for i, val in enumerate(actual):
            r = await self.inner.async_check(val, path + (i,))
            if not r.ok:
                errors.extend(r.errors)
                if first_failed_index is None:
                    first_failed_index = i
                    first_failed_inner = _pick_representative_error(list(r.errors))
        if errors:
            witness: dict[str, Any] = {
                "mode": "list_of",
                "first_failed_index": first_failed_index,
                "actual_witness": actual[:12],
            }
            if first_failed_inner is not None:
                witness["inner_error"] = _error_payload(first_failed_inner)
            outer = MatchError(
                path=path if first_failed_index is None else path + (first_failed_index,),
                code="list_of_element_mismatch",
                message=(
                    f"list item at index {first_failed_index} did not match the list_of matcher"
                    if first_failed_index is not None
                    else "one or more list items did not match the list_of matcher"
                ),
                expected="every list item to match the inner matcher",
                actual=_short_repr(actual),
                witness_json=json.dumps(witness, default=str),
            )
            if first_failed_inner is not None and first_failed_index is not None:
                outer = MatchError(
                    path=outer.path,
                    code=outer.code,
                    message=(
                        f"{outer.message}; representative mismatch at index {first_failed_index}: "
                        f"{first_failed_inner.message}"
                    ),
                    expected=outer.expected,
                    actual=outer.actual,
                    witness_json=outer.witness_json,
                )
            return MatchResult(ok=False, errors=(outer, *tuple(errors)))
        return MatchResult.success()


def list_of_matcher(inner: Any) -> ListOfMatcher:
    return ListOfMatcher(inner=coerce_any(inner))
