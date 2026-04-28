"""Scalar matchers: equality, predicates, strings, numbers, regex, one_of/all_of/not_, optional, any."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr


@dataclass(frozen=True, slots=True)
class EqualityMatcher(BaseMatcher):
    expected: Any

    def check(self, actual: Any, path: Path) -> MatchResult:
        if actual == self.expected:
            return MatchResult.success()
        return MatchResult.failure(
            MatchError(
                path=path,
                code="equality",
                message="value does not equal expected",
                expected=_short_repr(self.expected),
                actual=_short_repr(actual),
            )
        )


@dataclass(frozen=True, slots=True)
class PredicateMatcher(BaseMatcher):
    fn: Any
    message: str | None

    def check(self, actual: Any, path: Path) -> MatchResult:
        try:
            ok = bool(self.fn(actual))
        except Exception as e:  # noqa: BLE001 — surface user predicate bugs as failures
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="predicate",
                    message=f"predicate raised: {e}",
                    expected=self.message or "predicate must return truthy",
                    actual=_short_repr(actual),
                )
            )
        if ok:
            return MatchResult.success()
        msg = self.message or "predicate failed"
        return MatchResult.failure(
            MatchError(
                path=path,
                code="predicate",
                message=msg,
                expected=msg,
                actual=_short_repr(actual),
            )
        )


@dataclass(frozen=True, slots=True)
class AnyValueMatcher(BaseMatcher):
    def check(self, actual: Any, path: Path) -> MatchResult:  # noqa: ARG002
        return MatchResult.success()


@dataclass(frozen=True, slots=True)
class StringMatcher(BaseMatcher):
    min_len: int | None = None
    max_len: int | None = None
    pattern: re.Pattern[str] | None = None

    def check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, str):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="string",
                    message="expected a string",
                    expected="str",
                    actual=type(actual).__name__,
                )
            )
        if self.min_len is not None and len(actual) < self.min_len:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="string",
                    message=f"string shorter than min_len={self.min_len}",
                    expected=f"len >= {self.min_len}",
                    actual=str(len(actual)),
                )
            )
        if self.max_len is not None and len(actual) > self.max_len:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="string",
                    message=f"string longer than max_len={self.max_len}",
                    expected=f"len <= {self.max_len}",
                    actual=str(len(actual)),
                )
            )
        if self.pattern is not None and self.pattern.fullmatch(actual) is None:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="string",
                    message="string does not fully match pattern",
                    expected=self.pattern.pattern,
                    actual=_short_repr(actual),
                )
            )
        return MatchResult.success()


@dataclass(frozen=True, slots=True)
class NumberMatcher(BaseMatcher):
    min: float | int | None = None
    max: float | int | None = None
    int_only: bool = False

    def check(self, actual: Any, path: Path) -> MatchResult:
        if isinstance(actual, bool):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="number",
                    message="expected a number, not bool",
                    expected="int | float",
                    actual="bool",
                )
            )
        if self.int_only and not isinstance(actual, int):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="number",
                    message="expected an int",
                    expected="int",
                    actual=type(actual).__name__,
                )
            )
        if not isinstance(actual, (int, float)):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="number",
                    message="expected a number",
                    expected="int | float",
                    actual=type(actual).__name__,
                )
            )
        n = float(actual)
        if self.min is not None and n < float(self.min):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="number",
                    message=f"value below min={self.min}",
                    expected=f">= {self.min}",
                    actual=_short_repr(actual),
                )
            )
        if self.max is not None and n > float(self.max):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="number",
                    message=f"value above max={self.max}",
                    expected=f"<= {self.max}",
                    actual=_short_repr(actual),
                )
            )
        return MatchResult.success()


@dataclass(frozen=True, slots=True)
class RegexMatcher(BaseMatcher):
    pattern: re.Pattern[str]

    def check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, str):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="regex",
                    message="expected a string for regex match",
                    expected=f"str matching {self.pattern.pattern!r}",
                    actual=type(actual).__name__,
                )
            )
        if self.pattern.fullmatch(actual) is not None:
            return MatchResult.success()
        return MatchResult.failure(
            MatchError(
                path=path,
                code="regex",
                message="string does not fully match pattern",
                expected=self.pattern.pattern,
                actual=_short_repr(actual),
            )
        )


@dataclass(frozen=True, slots=True)
class OneOfMatcher(BaseMatcher):
    options: tuple[BaseMatcher, ...]

    def check(self, actual: Any, path: Path) -> MatchResult:
        for opt in self.options:
            r = opt.check(actual, path)
            if r.ok:
                return MatchResult.success()
        joined = ", ".join(_matcher_summary(o) for o in self.options)
        return MatchResult.failure(
            MatchError(
                path=path,
                code="one_of",
                message="value does not match any option",
                expected=f"one of ({joined})",
                actual=_short_repr(actual),
            )
        )

    async def async_check(self, actual: Any, path: Path) -> MatchResult:
        for opt in self.options:
            r = await opt.async_check(actual, path)
            if r.ok:
                return MatchResult.success()
        joined = ", ".join(_matcher_summary(o) for o in self.options)
        return MatchResult.failure(
            MatchError(
                path=path,
                code="one_of",
                message="value does not match any option",
                expected=f"one of ({joined})",
                actual=_short_repr(actual),
            )
        )


@dataclass(frozen=True, slots=True)
class AllOfMatcher(BaseMatcher):
    options: tuple[BaseMatcher, ...]

    def check(self, actual: Any, path: Path) -> MatchResult:
        errors: list[MatchError] = []
        for opt in self.options:
            r = opt.check(actual, path)
            if not r.ok:
                errors.extend(r.errors)
        if errors:
            return MatchResult(ok=False, errors=tuple(errors))
        return MatchResult.success()

    async def async_check(self, actual: Any, path: Path) -> MatchResult:
        errors: list[MatchError] = []
        for opt in self.options:
            r = await opt.async_check(actual, path)
            if not r.ok:
                errors.extend(r.errors)
        if errors:
            return MatchResult(ok=False, errors=tuple(errors))
        return MatchResult.success()


@dataclass(frozen=True, slots=True)
class NotMatcher(BaseMatcher):
    inner: BaseMatcher

    def check(self, actual: Any, path: Path) -> MatchResult:
        r = self.inner.check(actual, path)
        if not r.ok:
            return MatchResult.success()
        return MatchResult.failure(
            MatchError(
                path=path,
                code="not",
                message="value matches disallowed spec",
                expected=f"not {_matcher_summary(self.inner)}",
                actual=_short_repr(actual),
            )
        )

    async def async_check(self, actual: Any, path: Path) -> MatchResult:
        r = await self.inner.async_check(actual, path)
        if not r.ok:
            return MatchResult.success()
        return MatchResult.failure(
            MatchError(
                path=path,
                code="not",
                message="value matches disallowed spec",
                expected=f"not {_matcher_summary(self.inner)}",
                actual=_short_repr(actual),
            )
        )


def _matcher_summary(m: BaseMatcher) -> str:
    if isinstance(m, EqualityMatcher):
        return _short_repr(m.expected)
    return type(m).__name__


@dataclass(frozen=True, slots=True)
class OptionalMatcher(BaseMatcher):
    inner: BaseMatcher

    def check(self, actual: Any, path: Path) -> MatchResult:
        if actual is None:
            return MatchResult.success()
        return self.inner.check(actual, path)

    async def async_check(self, actual: Any, path: Path) -> MatchResult:
        if actual is None:
            return MatchResult.success()
        return await self.inner.async_check(actual, path)


def one_of_matcher(*options: Any) -> OneOfMatcher:
    coerced = tuple(coerce_any(o) for o in options)
    return OneOfMatcher(options=coerced)


def all_of_matcher(*options: Any) -> AllOfMatcher:
    coerced = tuple(coerce_any(o) for o in options)
    return AllOfMatcher(options=coerced)


def not_matcher(inner: Any) -> NotMatcher:
    return NotMatcher(inner=coerce_any(inner))


def optional_matcher(inner: Any) -> OptionalMatcher:
    return OptionalMatcher(inner=coerce_any(inner))
