"""Human-readable string representations of matcher specs for failure panels."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import Path, PathPart, _short_repr

Visibility = Literal["full", "focus", "on_path", "stub", "omit"]

_TOOL_CALL_KW_KEYS = ("args", "result", "error", "metadata", "children")


def _relation(path: Path, focus: Path) -> Visibility:
    if not focus:
        return "full"
    if path == focus:
        return "focus"
    prefix_len = 0
    for a, b in zip(path, focus, strict=False):
        if a == b:
            prefix_len += 1
        else:
            break
    if len(path) < len(focus) and path == focus[: len(path)]:
        return "on_path"
    if prefix_len == len(focus) and len(path) > len(focus):
        return "omit"
    if prefix_len < len(path) or prefix_len < len(focus):
        return "stub"
    return "stub"


def _tool_call_literal_name(matcher: BaseMatcher) -> str | None:
    from agent_spec_kit.match.object import ObjectMatcher
    from agent_spec_kit.match.scalars import EqualityMatcher

    if not isinstance(matcher, ObjectMatcher):
        return None
    name_m = matcher.props.get("name")
    if isinstance(name_m, EqualityMatcher) and isinstance(name_m.expected, str):
        return name_m.expected
    return None


def _is_tool_call_object(matcher: BaseMatcher) -> bool:
    from agent_spec_kit.match.object import ObjectMatcher

    return isinstance(matcher, ObjectMatcher) and "name" in matcher.props


def _stub_repr(matcher: BaseMatcher) -> str:
    name = _tool_call_literal_name(matcher)
    if name is not None:
        return f'tool_call("{name}")'
    if _is_tool_call_object(matcher):
        return "tool_call(...)"
    return matcher_summary(matcher)


def _join_kv(parts: list[str]) -> str:
    return ", ".join(parts)


def _format_rules(matcher: BaseMatcher) -> str | None:
    from agent_spec_kit.match.object import ObjectMatcher

    if not isinstance(matcher, ObjectMatcher) or not matcher.rules:
        return None
    return ", ".join(rule.describe() for rule in matcher.rules)


def _format_where(matcher: BaseMatcher) -> str | None:
    from agent_spec_kit.match.object import ObjectMatcher

    if not isinstance(matcher, ObjectMatcher) or not matcher.where_hooks:
        return None
    return ", ".join(msg for _, msg in matcher.where_hooks)


def format_matcher(
    matcher: BaseMatcher,
    *,
    path: Path = (),
    focus_path: Path = (),
) -> str:
    """Render a matcher; truncate branches off ``focus_path`` when set."""
    vis = _relation(path, focus_path)
    if vis == "omit":
        return "..."
    if vis == "stub":
        return _stub_repr(matcher)

    from agent_spec_kit.match.forbidden import ForbiddenToolCallsMatcher
    from agent_spec_kit.match.lists import ListMatcher, ListOfMatcher
    from agent_spec_kit.match.llm_criteria import LLMCriteriaMatcher
    from agent_spec_kit.match.object import ObjectMatcher
    from agent_spec_kit.match.scalars import (
        AllOfMatcher,
        AnyValueMatcher,
        EqualityMatcher,
        NotMatcher,
        NumberMatcher,
        OneOfMatcher,
        OptionalMatcher,
        PredicateMatcher,
        RegexMatcher,
        StringMatcher,
    )
    from agent_spec_kit.match.transform import TransformMatcher

    if isinstance(matcher, EqualityMatcher):
        return _short_repr(matcher.expected)

    if _is_tool_call_object(matcher):
        return _format_tool_call(matcher, path=path, focus_path=focus_path)

    if isinstance(matcher, ObjectMatcher):
        return _format_object(matcher, path=path, focus_path=focus_path)

    if isinstance(matcher, ListMatcher):
        return _format_list_matcher(matcher, path=path, focus_path=focus_path)

    if isinstance(matcher, ListOfMatcher):
        inner = format_matcher(matcher.inner, path=path, focus_path=focus_path)
        return f"list_of({inner})"

    if isinstance(matcher, StringMatcher):
        parts: list[str] = []
        if matcher.min_len is not None:
            parts.append(f"min_len={matcher.min_len}")
        if matcher.max_len is not None:
            parts.append(f"max_len={matcher.max_len}")
        if matcher.pattern is not None:
            parts.append(f"pattern={matcher.pattern.pattern!r}")
        return f"string({', '.join(parts)})" if parts else "string()"

    if isinstance(matcher, NumberMatcher):
        parts = []
        if matcher.min is not None:
            parts.append(f"min={matcher.min}")
        if matcher.max is not None:
            parts.append(f"max={matcher.max}")
        if matcher.int_only:
            parts.append("int_only=True")
        return f"number({', '.join(parts)})" if parts else "number()"

    if isinstance(matcher, RegexMatcher):
        return f"regex({matcher.pattern.pattern!r})"

    if isinstance(matcher, PredicateMatcher):
        if matcher.message:
            return _short_repr(matcher.message)
        return "<predicate>"

    if isinstance(matcher, OptionalMatcher):
        inner = format_matcher(matcher.inner, path=path, focus_path=focus_path)
        return f"optional({inner})"

    if isinstance(matcher, OneOfMatcher):
        opts = ", ".join(format_matcher(o, path=path, focus_path=focus_path) for o in matcher.options)
        return f"one_of({opts})"

    if isinstance(matcher, AllOfMatcher):
        opts = ", ".join(format_matcher(o, path=path, focus_path=focus_path) for o in matcher.options)
        return f"all_of({opts})"

    if isinstance(matcher, NotMatcher):
        inner = format_matcher(matcher.inner, path=path, focus_path=focus_path)
        return f"not({inner})"

    if isinstance(matcher, AnyValueMatcher):
        return "any_value()"

    if isinstance(matcher, TransformMatcher):
        inner = format_matcher(matcher.inner, path=path, focus_path=focus_path)
        return f"transform(<fn>, {inner})"

    if isinstance(matcher, ForbiddenToolCallsMatcher):
        parts = [
            format_matcher(f, path=path + (i,), focus_path=focus_path)
            for i, f in enumerate(matcher.forbidden)
        ]
        ordered = "ordered=True" if matcher.ordered else "ordered=False"
        return f"forbidden([{_join_kv(parts)}], {ordered})"

    if isinstance(matcher, LLMCriteriaMatcher):
        crit = [_short_repr(c, max_len=60) for c in matcher.criteria[:3]]
        if len(matcher.criteria) > 3:
            crit.append("...")
        return (
            f"llm_criteria({crit}, threshold={matcher.threshold}, "
            f"model={matcher.model!r})"
        )

    return type(matcher).__name__


def _format_tool_call(
    matcher: BaseMatcher,
    *,
    path: Path,
    focus_path: Path,
) -> str:
    from agent_spec_kit.match.object import ObjectMatcher

    assert isinstance(matcher, ObjectMatcher)
    lit_name = _tool_call_literal_name(matcher)
    parts: list[str] = []

    if lit_name is not None:
        parts.append(f"{lit_name!r}")
    elif "name" in matcher.props:
        name_path = path + ("name",)
        parts.append(
            f"name={format_matcher(matcher.props['name'], path=name_path, focus_path=focus_path)}"
        )

    for key in _TOOL_CALL_KW_KEYS:
        if key not in matcher.props:
            continue
        child_path = path + (key,)
        child_vis = _relation(child_path, focus_path)
        if child_vis == "omit":
            continue
        if child_vis == "stub":
            parts.append(f"{key}=...")
            continue
        formatted = format_matcher(matcher.props[key], path=child_path, focus_path=focus_path)
        parts.append(f"{key}={formatted}")

    return f"tool_call({_join_kv(parts)})"


def _format_object(
    matcher: BaseMatcher,
    *,
    path: Path,
    focus_path: Path,
) -> str:
    from agent_spec_kit.match.object import ObjectMatcher

    assert isinstance(matcher, ObjectMatcher)
    vis = _relation(path, focus_path)
    if vis == "stub":
        return _stub_repr(matcher)

    focus_key: PathPart | None = (
        focus_path[len(path)] if len(focus_path) > len(path) else None
    )
    show_all_fields = (
        focus_key is not None
        and not isinstance(focus_key, int)
        and focus_key not in matcher.props
    )

    field_parts: list[str] = []
    trailing: list[str] = []
    has_omitted = False

    for key, prop_m in matcher.props.items():
        child_path = path + (key,)
        if show_all_fields:
            formatted = format_matcher(prop_m, path=child_path, focus_path=())
            field_parts.append(f"{key!r}: {formatted}")
            continue
        child_vis = _relation(child_path, focus_path)
        if child_vis in ("omit", "stub"):
            has_omitted = True
            continue
        formatted = format_matcher(prop_m, path=child_path, focus_path=focus_path)
        field_parts.append(f"{key!r}: {formatted}")

    if has_omitted and field_parts:
        field_parts.append("...")

    body = "{" + ", ".join(field_parts) + "}"
    if matcher.extra != "forbid":
        trailing.append(f'extra="{matcher.extra}"')
    rules_s = _format_rules(matcher)
    if rules_s and vis in ("full", "focus", "on_path"):
        trailing.append(f"rules=[{rules_s}]")
    where_s = _format_where(matcher)
    if where_s and vis in ("full", "focus", "on_path"):
        trailing.append(f"where=[{where_s}]")

    if trailing:
        return f"object({body}, {_join_kv(trailing)})"
    return f"object({body})"


def _format_list_matcher(
    matcher: BaseMatcher,
    *,
    path: Path,
    focus_path: Path,
) -> str:
    from agent_spec_kit.match.lists import ListMatcher

    assert isinstance(matcher, ListMatcher)
    body = _format_list_elements(
        matcher.elements,
        path=path,
        focus_path=focus_path,
    )
    suffix_parts: list[str] = []
    if matcher.mode != "ordered":
        suffix_parts.append(f'mode="{matcher.mode}"')
    if matcher.allow_extras:
        suffix_parts.append("allow_extras=True")
    if suffix_parts:
        return f"list({body}, {_join_kv(suffix_parts)})"
    return f"list({body})"


def _format_list_elements(
    elements: Sequence[BaseMatcher],
    *,
    path: Path,
    focus_path: Path,
) -> str:
    if not elements:
        return "[]"

    focus_index: int | None = None
    if focus_path and len(focus_path) > len(path) and isinstance(focus_path[len(path)], int):
        focus_index = focus_path[len(path)]

    lines: list[str] = []
    for i, em in enumerate(elements):
        child_path = path + (i,)
        child_vis = _relation(child_path, focus_path)
        if child_vis == "omit" and focus_index is not None and abs(i - focus_index) > 1:
            continue
        formatted = format_matcher(em, path=child_path, focus_path=focus_path)
        lines.append(f"[{i}] {formatted}")

    if len(lines) > 4 and focus_index is not None:
        kept: list[str] = []
        for line in lines:
            idx = int(line.split("]", 1)[0][1:])
            if idx == 0 or idx == focus_index or idx == len(elements) - 1:
                kept.append(line)
            elif kept and kept[-1] != "  ...":
                kept.append("  ...")
        lines = kept

    if len(lines) == 1:
        return f"[{lines[0]}]"
    return "[\n  " + ",\n  ".join(lines) + "\n]"


def _unwrap_spec(spec: Any) -> tuple[list[BaseMatcher] | None, BaseMatcher | None]:
    """Return (list elements, single matcher) for display entry points."""
    from agent_spec_kit.match.forbidden import ForbiddenToolCallsMatcher
    from agent_spec_kit.match.lists import ListMatcher

    if isinstance(spec, ForbiddenToolCallsMatcher):
        return list(spec.forbidden), spec
    if isinstance(spec, ListMatcher):
        return list(spec.elements), spec
    if isinstance(spec, (list, tuple)):
        return [coerce_any(e) for e in spec], None
    if isinstance(spec, BaseMatcher):
        return None, spec
    try:
        coerced = coerce_any(spec)
    except TypeError:
        return None, None
    if isinstance(coerced, ListMatcher):
        return list(coerced.elements), coerced
    return None, coerced


def format_forbidden_spec(
    spec: Any,
    *,
    max_len: int = 600,
) -> str:
    """Render forbidden tool-call patterns (must-not-call wording)."""
    from agent_spec_kit.match.forbidden import ForbiddenToolCallsMatcher

    elements, root = _unwrap_spec(spec)
    if isinstance(root, ForbiddenToolCallsMatcher):
        patterns = list(root.forbidden)
    elif elements is not None:
        patterns = elements
    elif root is not None:
        patterns = [root]
    else:
        return _short_repr(spec, max_len=max_len)

    rendered = [
        format_matcher(p, path=(), focus_path=()) for p in patterns
    ]
    if len(rendered) == 1:
        text = f"must not call {rendered[0]}"
    else:
        text = "must not call:\n  " + "\n  ".join(rendered)

    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def format_spec_at_path(
    spec: Any,
    focus_path: Path,
    *,
    max_len: int = 600,
) -> str:
    """Render ``spec`` with branches off ``focus_path`` truncated."""
    elements, root = _unwrap_spec(spec)
    if elements is not None:
        text = _format_list_elements(elements, path=(), focus_path=focus_path)
    elif root is not None:
        text = format_matcher(root, path=(), focus_path=focus_path)
    else:
        return _short_repr(spec, max_len=max_len)

    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def matcher_summary(matcher: BaseMatcher) -> str:
    """Compact one-line summary for combinators (``one_of``, ``not_``, etc.)."""
    from agent_spec_kit.match.scalars import EqualityMatcher

    if isinstance(matcher, EqualityMatcher):
        return _short_repr(matcher.expected, max_len=80)
    name = _tool_call_literal_name(matcher)
    if name is not None:
        return f'tool_call("{name}")'
    return format_matcher(matcher, path=(), focus_path=())


__all__ = [
    "format_forbidden_spec",
    "format_matcher",
    "format_spec_at_path",
    "matcher_summary",
]
