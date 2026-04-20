"""List matchers: ordered/unordered with optional extras, homogeneous list_of."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Literal

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr

_MAX_PERM = 9  # exhaustive permutation search for multiset (factorial growth)


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
        return MatchResult.failure(
            MatchError(
                path=path,
                code="list",
                message=(
                    "wrong list length: expected exactly "
                    f"{len(elements)} value(s) in this order, found {len(actual)}"
                ),
                expected=str(len(elements)),
                actual=str(len(actual)),
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
                    code="list",
                    message=(
                        "could not find each expected value in order from left to right "
                        "(extra values in between are allowed)"
                    ),
                    expected="each value in order, left to right",
                    actual=_short_repr(actual),
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
            code="list",
            message=(
                "the list does not match when order is ignored: each expected value "
                "must correspond to a different position in the list"
            ),
            expected="each value matched to a different position (order ignored)",
            actual=_short_repr(actual),
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
            code="list",
            message=msg,
            expected=(
                "each value to a different item (order ignored, extras allowed)"
                if allow_extras
                else "each value to a different position (order ignored)"
            ),
            actual=_short_repr(actual),
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
                return MatchResult.failure(
                    MatchError(
                        path=path,
                        code="list",
                        message=(
                            "wrong list length: expected exactly "
                            f"{n} value(s) when order is ignored, found {m}"
                        ),
                        expected=str(n),
                        actual=str(m),
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
                    code="list",
                    message=(
                        "list is too short: need at least "
                        f"{n} item(s) to match all expected values (order does not matter)"
                    ),
                    expected=f">= {n}",
                    actual=str(m),
                )
            )
        if n == 0:
            return MatchResult.success()
        return _unordered_injective_dfs(specs, actual, path, allow_extras=True)


def list_matcher(
    *elements: Any,
    mode: Literal["ordered", "unordered"] = "ordered",
    allow_extras: bool = False,
) -> ListMatcher:
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
