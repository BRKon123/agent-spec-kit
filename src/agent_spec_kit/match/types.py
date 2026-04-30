"""Structured match results and errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PathPart = str | int
Path = tuple[PathPart, ...]


def path_to_str(path: Path) -> str:
    if not path:
        return "$"
    out = "$"
    for p in path:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += f".{p}"
    return out


def _short_repr(value: Any, *, max_len: int = 200) -> str:
    s = repr(value)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


@dataclass(frozen=True, slots=True)
class MatchError:
    """One failed constraint at a location in the value."""

    path: Path
    code: str
    message: str
    expected: str
    actual: str
    #: Optional JSON object with machine-readable witness (list length, slice indices, etc.).
    witness_json: str | None = None


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Outcome of matching a spec against an actual value."""

    ok: bool
    errors: tuple[MatchError, ...] = ()

    @staticmethod
    def success() -> MatchResult:
        return MatchResult(ok=True, errors=())

    @staticmethod
    def failure(*errors: MatchError) -> MatchResult:
        return MatchResult(ok=False, errors=tuple(errors))

    def merge(self, other: MatchResult) -> MatchResult:
        if self.ok and other.ok:
            return MatchResult.success()
        errs: list[MatchError] = []
        if not self.ok:
            errs.extend(self.errors)
        if not other.ok:
            errs.extend(other.errors)
        return MatchResult(ok=False, errors=tuple(errs))
