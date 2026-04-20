"""List matchers: exact order, multiset (unordered), homogeneous list_of."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr

_MAX_PERM = 9  # exhaustive permutation search for multiset (factorial growth)


@dataclass(frozen=True, slots=True)
class ListExactMatcher(BaseMatcher):
    elements: tuple[BaseMatcher, ...]

    def check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, list):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_exact",
                    message="expected a list",
                    expected="list",
                    actual=type(actual).__name__,
                )
            )
        if len(actual) != len(self.elements):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_exact",
                    message="list length mismatch",
                    expected=str(len(self.elements)),
                    actual=str(len(actual)),
                )
            )
        errors: list[MatchError] = []
        for i, (em, val) in enumerate(zip(self.elements, actual, strict=True)):
            r = em.check(val, path + (i,))
            if not r.ok:
                errors.extend(r.errors)
        if errors:
            return MatchResult(ok=False, errors=tuple(errors))
        return MatchResult.success()


@dataclass(frozen=True, slots=True)
class ListUnorderedMatcher(BaseMatcher):
    """Multiset semantics: multiplicity matters; order does not."""

    elements: tuple[BaseMatcher, ...]

    def check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, list):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_unordered",
                    message="expected a list",
                    expected="list",
                    actual=type(actual).__name__,
                )
            )
        n = len(self.elements)
        if len(actual) != n:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="list_unordered",
                    message="list length mismatch for multiset",
                    expected=str(n),
                    actual=str(len(actual)),
                )
            )
        specs = list(self.elements)
        if n == 0:
            return MatchResult.success()

        if n <= _MAX_PERM:
            return _multiset_by_permutation(specs, actual, path)

        return _multiset_by_dfs(specs, actual, path)


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
            code="list_unordered",
            message="no assignment of multiset elements matches actual list",
            expected="multiset match",
            actual=_short_repr(actual),
        )
    )


def _multiset_by_dfs(specs: list[BaseMatcher], actual: list[Any], path: Path) -> MatchResult:
    """Backtracking for larger n when exhaustive permutations are too expensive."""

    n = len(specs)
    used = [False] * n

    def dfs(i: int) -> bool:
        if i == n:
            return True
        for j in range(n):
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
    return MatchResult.failure(
        MatchError(
            path=path,
            code="list_unordered",
            message="no assignment of multiset elements matches actual list",
            expected="multiset match",
            actual=_short_repr(actual),
        )
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


def list_exact_matcher(*elements: Any) -> ListExactMatcher:
    return ListExactMatcher(elements=tuple(coerce_any(e) for e in elements))


def list_unordered_matcher(*elements: Any) -> ListUnorderedMatcher:
    return ListUnorderedMatcher(elements=tuple(coerce_any(e) for e in elements))


def list_of_matcher(inner: Any) -> ListOfMatcher:
    return ListOfMatcher(inner=coerce_any(inner))
