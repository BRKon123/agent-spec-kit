"""Transform-then-match wrapper."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr


@dataclass(frozen=True, slots=True)
class TransformMatcher(BaseMatcher):
    fn: Callable[[Any], Any]
    inner: BaseMatcher

    def check(self, actual: Any, path: Path) -> MatchResult:
        try:
            transformed = self.fn(actual)
        except Exception as e:  # noqa: BLE001
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="transform",
                    message=f"transform raised: {e}",
                    expected="transform without exception",
                    actual=_short_repr(actual),
                )
            )
        r = self.inner.check(transformed, path)
        if r.ok:
            return r
        # Re-wrap errors to mention transform context
        merged: list[MatchError] = []
        for err in r.errors:
            merged.append(
                MatchError(
                    path=err.path,
                    code=err.code,
                    message=f"after transform: {err.message}",
                    expected=err.expected,
                    actual=err.actual,
                )
            )
        return MatchResult(ok=False, errors=tuple(merged))


def transform_matcher(fn: Callable[[Any], Any], inner: Any) -> TransformMatcher:
    return TransformMatcher(fn=fn, inner=coerce_any(inner))
