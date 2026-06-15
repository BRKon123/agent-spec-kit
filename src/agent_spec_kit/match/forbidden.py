"""Matchers that forbid tool-call patterns in a trace."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr


def _coerce_forbidden_elements(spec: Any) -> tuple[BaseMatcher, ...]:
    elements = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    return tuple(coerce_any(el) for el in elements)


@dataclass(frozen=True, slots=True)
class ForbiddenToolCallsMatcher(BaseMatcher):
    """Fail when actual root tools match any forbidden pattern (or forbidden subsequence)."""

    forbidden: tuple[BaseMatcher, ...]
    ordered: bool

    def check(self, actual: Any, path: Path) -> MatchResult:
        if not isinstance(actual, list):
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="type_mismatch",
                    message=f"expected list of tool dicts, got {type(actual).__name__}",
                    expected="list",
                    actual=_short_repr(actual),
                )
            )
        if not self.forbidden:
            return MatchResult.success()

        if len(self.forbidden) == 1 or not self.ordered:
            return self._match_any_forbidden(actual, path)

        return self._match_forbidden_subsequence(actual, path)

    def _match_any_forbidden(self, actual: list[Any], path: Path) -> MatchResult:
        for idx, tool in enumerate(actual):
            for fidx, forbidden in enumerate(self.forbidden):
                r = forbidden.check(tool, path + (idx,))
                if r.ok:
                    name = _tool_name(tool)
                    fname = _expected_tool_name(forbidden) or f"pattern[{fidx}]"
                    return MatchResult.failure(
                        MatchError(
                            path=path + (idx,),
                            code="forbidden_tool_call",
                            message=(
                                f"forbidden tool call {fname!r} found at index {idx} "
                                f"(actual tool {name!r})"
                            ),
                            expected=f"no {fname!r}",
                            actual=_short_repr(tool),
                        )
                    )
        return MatchResult.success()

    def _match_forbidden_subsequence(self, actual: list[Any], path: Path) -> MatchResult:
        """Fail if forbidden patterns appear in order as a subsequence."""
        fi = 0
        matched_indices: list[int] = []
        for idx, tool in enumerate(actual):
            if fi >= len(self.forbidden):
                break
            r = self.forbidden[fi].check(tool, path + (idx,))
            if r.ok:
                matched_indices.append(idx)
                fi += 1
        if fi == len(self.forbidden):
            names = [_tool_name(actual[i]) for i in matched_indices]
            return MatchResult.failure(
                MatchError(
                    path=path + (matched_indices[0],),
                    code="forbidden_tool_sequence",
                    message=(
                        "forbidden ordered tool subsequence found at indices "
                        f"{matched_indices}: {' -> '.join(names)}"
                    ),
                    expected="forbidden sequence absent",
                    actual=names,
                )
            )
        return MatchResult.success()


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict) and "name" in tool:
        return str(tool["name"])
    return type(tool).__name__


def _expected_tool_name(matcher: BaseMatcher) -> str | None:
    from agent_spec_kit.match.object import ObjectMatcher
    from agent_spec_kit.match.scalars import EqualityMatcher

    if not isinstance(matcher, ObjectMatcher):
        return None
    name_m = matcher.props.get("name")
    if isinstance(name_m, EqualityMatcher) and isinstance(name_m.expected, str):
        return name_m.expected
    return None


def forbidden_tool_calls_matcher(
    spec: Any,
    *,
    ordered: bool = True,
) -> ForbiddenToolCallsMatcher:
    return ForbiddenToolCallsMatcher(
        forbidden=_coerce_forbidden_elements(spec),
        ordered=ordered,
    )
