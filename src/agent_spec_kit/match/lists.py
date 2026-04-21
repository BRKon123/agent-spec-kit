"""List matchers: ordered/unordered with optional extras, homogeneous list_of."""

from __future__ import annotations

import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr

_MAX_PERM = 9  # exhaustive permutation search for multiset (factorial growth)


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
    for i, (em, val) in enumerate(zip(elements, actual, strict=True)):
        r = em.check(val, path + (i,))
        if not r.ok:
            errors.extend(r.errors)
    if errors:
        return MatchResult(ok=False, errors=tuple(errors))
    return MatchResult.success()


def _ordered_subsequence(
    elements: tuple[BaseMatcher, ...], actual: list[Any], path: Path
) -> MatchResult:
    ai = 0
    for em in elements:
        while ai < len(actual):
            r = em.check(actual[ai], path + (ai,))
            if r.ok:
                ai += 1
                break
            ai += 1
        else:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="missing_element",
                    message=(
                        "could not find each expected value in order from left to right "
                        "(extra values in between are allowed)"
                    ),
                    expected="each value in order, left to right",
                    actual=_short_repr(actual),
                    witness_json=json.dumps(
                        {"mode": "ordered_subsequence", "actual_witness": actual[:12]},
                        default=str,
                    ),
                )
            )
    return MatchResult.success()


def _multiset_by_permutation(
    specs: list[BaseMatcher], actual: list[Any], path: Path
) -> MatchResult:
    n = len(specs)
    for perm in itertools.permutations(range(n)):
        for i, j in enumerate(perm):
            r = specs[i].check(actual[j], path + (j,))
            if not r.ok:
                break
        else:
            return MatchResult.success()
    return MatchResult.failure(
        MatchError(
            path=path,
            code="unordered_mismatch",
            message=(
                "the list does not match when order is ignored: each expected value "
                "must correspond to a different position in the list"
            ),
            expected="each value matched to a different position (order ignored)",
            actual=_short_repr(actual),
            witness_json=json.dumps(
                {"mode": "unordered_permutation", "actual_witness": actual[:12]},
                default=str,
            ),
        )
    )


def _unordered_injective_dfs(
    specs: list[BaseMatcher], actual: list[Any], path: Path, *, allow_extras: bool
) -> MatchResult:
    n = len(specs)
    m = len(actual)
    used = [False] * m

    def dfs(i: int) -> bool:
        if i == n:
            return True
        for j in range(m):
            if used[j]:
                continue
            r = specs[i].check(actual[j], path + (j,))
            if not r.ok:
                continue
            used[j] = True
            if dfs(i + 1):
                return True
            used[j] = False
        return False

    if dfs(0):
        return MatchResult.success()
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
    return MatchResult.failure(
        MatchError(
            path=path,
            code="unordered_mismatch",
            message=msg,
            expected=(
                "each value to a different item (order ignored, extras allowed)"
                if allow_extras
                else "each value to a different position (order ignored)"
            ),
            actual=_short_repr(actual),
            witness_json=json.dumps(
                {
                    "mode": "unordered_injective",
                    "allow_extras": allow_extras,
                    "actual_witness": actual[:12],
                },
                default=str,
            ),
        )
    )


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
        for i, val in enumerate(actual):
            r = self.inner.check(val, path + (i,))
            if not r.ok:
                errors.extend(r.errors)
        if errors:
            return MatchResult(ok=False, errors=tuple(errors))
        return MatchResult.success()


def list_of_matcher(inner: Any) -> ListOfMatcher:
    return ListOfMatcher(inner=coerce_any(inner))
