"""Public matcher combinators, :func:`match` (build spec), and :func:`check` (run)."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, overload

from agent_spec_kit.match.lists import (
    ListExactMatcher,
    ListOfMatcher,
    ListUnorderedMatcher,
    list_exact_matcher,
    list_of_matcher,
    list_unordered_matcher,
)
from agent_spec_kit.match.object import ExtraPolicy, ObjectMatcher, object_matcher
from agent_spec_kit.match.protocol import BaseMatcher, coerce_any, _is_predicate_callable
from agent_spec_kit.match.rules import (
    ForbidRule,
    RequireRule,
    Rule,
    field,
    forbid,
    require,
)
from agent_spec_kit.match.scalars import (
    AnyValueMatcher,
    NumberMatcher,
    PredicateMatcher,
    RegexMatcher,
    StringMatcher,
    one_of_matcher,
    optional_matcher,
)
from agent_spec_kit.match.transform import TransformMatcher, transform_matcher
from agent_spec_kit.match.types import MatchError, MatchResult, Path

_NO = object()


@overload
def check(spec: Any, actual: Any) -> MatchResult: ...


@overload
def check(spec: Any, *, actual: Any) -> MatchResult: ...


def check(spec: Any, actual_pos: Any = _NO, *, actual: Any = _NO) -> MatchResult:
    """
    Run a spec against a value: coerce ``spec`` and return a :class:`MatchResult`.

    Use ``check(spec, actual)`` or ``check(spec, actual=value)``.
    """
    if actual_pos is not _NO and actual is not _NO:
        raise TypeError("check() accepts at most one actual value (positional or actual=)")
    value = actual if actual_pos is _NO else actual_pos
    if value is _NO:
        raise TypeError("check(spec, actual) requires the value to validate")
    return coerce_any(spec).check(value, ())


@overload
def match(spec: Any, *, message: str) -> PredicateMatcher: ...


@overload
def match(spec: Any, *, message: None = None) -> BaseMatcher: ...


def match(spec: Any, *, message: str | None = None) -> BaseMatcher:
    """
    Build a matcher (no execution):

    - ``match(fn, message=\"...\")`` — :class:`PredicateMatcher` with a custom failure message.
    - ``match(spec)`` or ``match(spec, message=None)`` — coerce ``spec`` to a :class:`BaseMatcher`
      for embedding (literals, dict/list, combinators, bare callables, etc.).

    To validate a value, use :func:`check`.
    """
    if message is not None:
        if not _is_predicate_callable(spec):
            raise TypeError("message= requires a predicate callable")
        return PredicateMatcher(spec, message=message)
    return coerce_any(spec)


def any_value() -> AnyValueMatcher:
    return AnyValueMatcher()


def string(
    *,
    min_len: int | None = None,
    max_len: int | None = None,
    pattern: str | re.Pattern[str] | None = None,
) -> StringMatcher:
    pat = re.compile(pattern) if isinstance(pattern, str) else pattern
    return StringMatcher(min_len=min_len, max_len=max_len, pattern=pat)


def number(
    *,
    min: float | int | None = None,
    max: float | int | None = None,
    int_only: bool = False,
) -> NumberMatcher:
    return NumberMatcher(min=min, max=max, int_only=int_only)


def regex(pattern: str | re.Pattern[str]) -> RegexMatcher:
    p = re.compile(pattern) if isinstance(pattern, str) else pattern
    return RegexMatcher(p)


def one_of(*options: Any) -> Any:
    return one_of_matcher(*options)


def optional(inner: Any) -> Any:
    return optional_matcher(inner)


def object(  # noqa: A001
    mapping: Mapping[str, Any],
    *,
    extra: ExtraPolicy = "forbid",
    rules: Sequence[Rule] | None = None,
) -> ObjectMatcher:
    return object_matcher(mapping, extra=extra, rules=rules)


def list_exact(*elements: Any) -> ListExactMatcher:
    return list_exact_matcher(*elements)


def list_unordered(*elements: Any) -> ListUnorderedMatcher:
    return list_unordered_matcher(*elements)


def list_of(inner: Any) -> ListOfMatcher:
    return list_of_matcher(inner)


def transform(fn: Callable[[Any], Any], inner: Any) -> TransformMatcher:
    return transform_matcher(fn, inner)


__all__ = [
    "BaseMatcher",
    "ForbidRule",
    "ListExactMatcher",
    "ListOfMatcher",
    "ListUnorderedMatcher",
    "MatchError",
    "MatchResult",
    "ObjectMatcher",
    "Path",
    "PredicateMatcher",
    "RequireRule",
    "RegexMatcher",
    "Rule",
    "TransformMatcher",
    "any_value",
    "field",
    "forbid",
    "list_exact",
    "list_of",
    "list_unordered",
    "check",
    "match",
    "number",
    "object",
    "one_of",
    "optional",
    "regex",
    "require",
    "string",
    "transform",
]
