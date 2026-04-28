"""Public matcher combinators for building specs, and :func:`check` to validate values.

Build a spec from literals (nested ``dict`` / ``list``), :func:`object`, :func:`list`,
:func:`string`, :func:`optional`, etc., then run ``check(spec, actual)`` or
``check(spec, actual=value)``. Use :func:`match` to turn a value into an explicit
:class:`~agent_spec_kit.match.protocol.BaseMatcher` for embedding.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

from agent_spec_kit.match.llm_criteria import LLMCriteriaMatcher, llm_criteria_matcher
from agent_spec_kit.match.lists import (
    ListMatcher,
    ListOfMatcher,
    list_matcher,
    list_of_matcher,
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
    AllOfMatcher,
    AnyValueMatcher,
    NotMatcher,
    NumberMatcher,
    PredicateMatcher,
    RegexMatcher,
    StringMatcher,
    all_of_matcher,
    not_matcher,
    one_of_matcher,
    optional_matcher,
)
from agent_spec_kit.match.transform import TransformMatcher, transform_matcher
from agent_spec_kit.match.types import MatchError, MatchResult, Path

_NO = object()
_MISSING = object()


def check(spec: Any, actual_pos: Any = _NO, *, actual: Any = _NO) -> MatchResult:
    """Validate ``actual`` against ``spec`` and return a :class:`MatchResult`.

    ``spec`` is coerced to a matcher (see :func:`match`). On success ``result.ok`` is
    True; on failure ``result.errors`` lists :class:`MatchError` instances with paths.

    Call as ``check(spec, actual)`` or ``check(spec, actual=value)`` (not both).
    """
    if actual_pos is not _NO and actual is not _NO:
        raise TypeError("check() accepts at most one actual value (positional or actual=)")
    value = actual if actual_pos is _NO else actual_pos
    if value is _NO:
        raise TypeError("check(spec, actual) requires the value to validate")
    return coerce_any(spec).check(value, ())


async def async_check(spec: Any, actual_pos: Any = _NO, *, actual: Any = _NO) -> MatchResult:
    """Async version of :func:`check`; supports both sync and async matchers."""
    if actual_pos is not _NO and actual is not _NO:
        raise TypeError("async_check() accepts at most one actual value (positional or actual=)")
    value = actual if actual_pos is _NO else actual_pos
    if value is _NO:
        raise TypeError("async_check(spec, actual) requires the value to validate")
    return await coerce_any(spec).async_check(value, ())


def match(spec: Any, *, message: str | None = None) -> BaseMatcher:
    """Build a matcher without running it (use :func:`check` to validate a value).

    - ``match(fn, message="...")`` — wrap a predicate callable; failure uses your message.
    - ``match(spec)`` — coerce ``spec`` to a :class:`BaseMatcher` (literals, nested
      ``dict``/``list``, combinators, or a plain callable predicate with a generic message).

    Use this when you need to embed a coerced spec inside another combinator.
    """
    if message is not None:
        if not _is_predicate_callable(spec):
            raise TypeError("message= requires a predicate callable")
        return PredicateMatcher(spec, message=message)
    return coerce_any(spec)


def any_value() -> AnyValueMatcher:
    """Accept any value at this position (the check always succeeds)."""
    return AnyValueMatcher()


def string(
    *,
    min_len: int | None = None,
    max_len: int | None = None,
    pattern: str | re.Pattern[str] | None = None,
) -> StringMatcher:
    """Require a string ``actual``, optionally with min/max length or a regex pattern."""
    pat = re.compile(pattern) if isinstance(pattern, str) else pattern
    return StringMatcher(min_len=min_len, max_len=max_len, pattern=pat)


def number(
    *,
    min: float | int | None = None,
    max: float | int | None = None,
    int_only: bool = False,
) -> NumberMatcher:
    """Require a numeric ``actual``; optionally clamp to a range or require integers."""
    return NumberMatcher(min=min, max=max, int_only=int_only)


def regex(pattern: str | re.Pattern[str]) -> RegexMatcher:
    """Require ``actual`` to be a string that fully matches the regex (``fullmatch``)."""
    p = re.compile(pattern) if isinstance(pattern, str) else pattern
    return RegexMatcher(p)


def one_of(*options: Any) -> Any:
    """Require ``actual`` to satisfy at least one of the given specs (first match wins)."""
    return one_of_matcher(*options)


def all_of(*options: Any) -> Any:
    """Require ``actual`` to satisfy all given specs (AND semantics)."""
    return all_of_matcher(*options)


def not_(inner: Any) -> Any:
    """Require ``actual`` to not satisfy ``inner``."""
    return not_matcher(inner)


def optional(inner: Any) -> Any:
    """Allow ``None`` at this position, or otherwise match ``inner``.

    Use in :func:`object` field specs so the key may be missing, present with ``None``,
    or present with a value that matches ``inner``.
    """
    return optional_matcher(inner)


def object(  # noqa: A001
    mapping: Mapping[str, Any],
    *,
    extra: ExtraPolicy = "forbid",
    rules: Sequence[Rule] | None = None,
) -> ObjectMatcher:
    """Match dict-like values (``dict``, dataclass, Pydantic model, etc.).

    ``mapping`` maps each key to a spec (literal or matcher). ``extra="forbid"`` rejects
    keys not listed; ``extra="ignore"`` allows additional keys. ``rules`` adds
    conditional :func:`require` / :func:`forbid` rules using :func:`field` conditions.

    Chain ``.where(fn, "message")`` on the result for a whole-object check (see
    :class:`ObjectMatcher`).
    """
    return object_matcher(mapping, extra=extra, rules=rules)


def list(  # noqa: A001
    elements: Sequence[Any],
    *,
    mode: Literal["ordered", "unordered"] = "ordered",
    allow_extras: bool = False,
) -> ListMatcher:
    """Match a list with a fixed sequence of per-element specs.

    Pass specs as a single sequence (same shape as tool-call lists), e.g.
    ``list([a, b, c], mode=..., allow_extras=...)``.

    - ``mode="ordered"`` (default): elements must match in order. If ``allow_extras`` is
      False, lengths must match. If True, each spec must match some item in order, left
      to right (extra items in the list are skipped).
    - ``mode="unordered"``: order does not matter; each spec must match a different list
      item. If ``allow_extras`` is True, the list may be longer than ``elements``.

    For every item the same shape, use :func:`list_of` instead.
    """
    return list_matcher(elements, mode=mode, allow_extras=allow_extras)


def list_of(inner: Any) -> ListOfMatcher:
    """Match a list where every element matches the same ``inner`` spec.

    Use this for homogeneous lists (e.g. a list of objects). For a fixed tuple of
    different expectations, use :func:`list`.
    """
    return list_of_matcher(inner)


def transform(fn: Callable[[Any], Any], inner: Any) -> TransformMatcher:
    """Apply ``fn`` to ``actual``, then run ``inner`` on the transformed value.

    Useful when the wire format differs from what you want to validate (e.g. string to int).
    """
    return transform_matcher(fn, inner)


def contains(substring: str) -> PredicateMatcher:
    """Match when ``substring`` appears in ``str(actual)``."""

    def pred(actual: Any) -> bool:
        try:
            return substring in str(actual)
        except Exception:
            return False

    return PredicateMatcher(
        pred,
        message=f"expected value to contain substring {substring!r}",
    )


def tool_call(
    name: str,
    *,
    args: Any = _MISSING,
    result: Any = _MISSING,
    error: Any = _MISSING,
    metadata: Any = _MISSING,
    children: Any = _MISSING,
) -> ObjectMatcher:
    """Build an object matcher for one normalized tool-call dict (``name``, ``args``, …).

    ``args``, ``result``, ``error``, ``metadata``, and ``children`` are keyword-only.
    Omitted fields are not constrained (``extra="ignore"`` on the object matcher).
    """
    fields: dict[str, Any] = {"name": name}
    if args is not _MISSING:
        fields["args"] = args
    if result is not _MISSING:
        fields["result"] = result
    if error is not _MISSING:
        fields["error"] = error
    if metadata is not _MISSING:
        fields["metadata"] = metadata
    if children is not _MISSING:
        fields["children"] = children
    return object_matcher(fields, extra="ignore")


def llm_criteria(
    *,
    criteria: Sequence[str],
    threshold: int,
    model: str,
    temperature: float | None = None,
    timeout_s: float | None = None,
    judge_context: str | None = None,
    judge_fn: Callable[[str, Sequence[str], str | None], Any] | None = None,
    evaluation_mode: Literal["single", "per_criterion"] = "single",
) -> LLMCriteriaMatcher:
    """Judge ``actual`` text against criteria with an LLM and threshold."""
    return llm_criteria_matcher(
        criteria=criteria,
        threshold=threshold,
        model=model,
        temperature=temperature,
        timeout_s=timeout_s,
        judge_context=judge_context,
        judge_fn=judge_fn,
        evaluation_mode=evaluation_mode,
    )


__all__ = [
    "BaseMatcher",
    "ForbidRule",
    "AllOfMatcher",
    "ListMatcher",
    "ListOfMatcher",
    "MatchError",
    "MatchResult",
    "ObjectMatcher",
    "Path",
    "NotMatcher",
    "PredicateMatcher",
    "RequireRule",
    "RegexMatcher",
    "Rule",
    "TransformMatcher",
    "any_value",
    "field",
    "forbid",
    "list",
    "list_of",
    "check",
    "async_check",
    "contains",
    "all_of",
    "match",
    "number",
    "not_",
    "object",
    "one_of",
    "optional",
    "regex",
    "require",
    "string",
    "tool_call",
    "transform",
    "llm_criteria",
]
