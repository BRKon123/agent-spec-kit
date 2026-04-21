"""Structured scenario failures and counterexamples for reporting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.match.types import MatchError, MatchResult


def _path_to_str(path: tuple[Any, ...]) -> str:
    if not path:
        return "$"
    out = "$"
    for p in path:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += f".{p}"
    return out


def _short(s: str, max_len: int = 400) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


@dataclass(slots=True)
class FailureRecord:
    scenario_name: str
    step_index: int
    step_kind: str
    turn_index: int | None
    actual: Any
    matcher_spec: Any | None
    matcher_errors: tuple[MatchError, ...]
    error: BaseException | None = None


@dataclass(slots=True)
class Counterexample:
    headline: str
    location: str
    path: str | None
    expected_summary: str
    actual_min: Any
    notes: tuple[str, ...] = ()


class ScenarioAssertionFailed(AssertionError):
    """Assertion failed during a scenario; carries a structured counterexample."""

    def __init__(self, counterexample: Counterexample, *, record: FailureRecord | None = None):
        super().__init__(counterexample.headline)
        self.counterexample = counterexample
        self.record = record


def _witness_dict(err: MatchError) -> dict[str, Any]:
    if not err.witness_json:
        return {}
    try:
        return json.loads(err.witness_json)
    except json.JSONDecodeError:
        return {}


def counterexample_from_failure(record: FailureRecord) -> Counterexample:
    """Build a counterexample from a failure record (matcher-first, display caps)."""
    loc = f"step {record.step_index}"
    if record.turn_index is not None:
        loc += f", turn {record.turn_index}"
    if record.matcher_errors:
        err = record.matcher_errors[0]
        path_s = _path_to_str(err.path)
        wit = _witness_dict(err)
        actual_min: Any = wit.get("actual_witness", record.actual)
        if isinstance(actual_min, (dict, list)):
            try:
                actual_str = json.dumps(actual_min, default=str, indent=2)
            except TypeError:
                actual_str = repr(actual_min)
        else:
            actual_str = str(actual_min)
        actual_str = _short(actual_str, 800)
        notes: list[str] = []
        if len(record.matcher_errors) > 1:
            notes.append(f"(+{len(record.matcher_errors) - 1} more matcher error(s))")
        return Counterexample(
            headline=f"{record.scenario_name}: {err.message}",
            location=loc,
            path=path_s,
            expected_summary=_short(f"{err.code}: expected {err.expected}", 200),
            actual_min=actual_str,
            notes=tuple(notes),
        )
    if record.error is not None:
        msg = str(record.error) or type(record.error).__name__
        return Counterexample(
            headline=f"{record.scenario_name}: {msg}",
            location=loc,
            path=None,
            expected_summary=type(record.error).__name__,
            actual_min=_short(repr(record.actual), 400),
            notes=(),
        )
    return Counterexample(
        headline=f"{record.scenario_name}: assertion failed",
        location=loc,
        path=None,
        expected_summary="(no matcher errors)",
        actual_min=record.actual,
        notes=(),
    )


def raise_scenario_match_failure(
    *,
    scenario_name: str,
    step_index: int,
    step_kind: str,
    turn_index: int | None,
    result: MatchResult,
    matcher_spec: Any,
    actual: Any,
    headline_prefix: str = "",
) -> None:
    """Raise :class:`ScenarioAssertionFailed` from a failed :class:`MatchResult`."""
    record = FailureRecord(
        scenario_name=scenario_name,
        step_index=step_index,
        step_kind=step_kind,
        turn_index=turn_index,
        actual=actual,
        matcher_spec=matcher_spec,
        matcher_errors=result.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    if headline_prefix:
        cx = Counterexample(
            headline=f"{headline_prefix}: {cx.headline}",
            location=cx.location,
            path=cx.path,
            expected_summary=cx.expected_summary,
            actual_min=cx.actual_min,
            notes=cx.notes,
        )
    raise ScenarioAssertionFailed(cx, record=record) from None


__all__ = [
    "Counterexample",
    "FailureRecord",
    "ScenarioAssertionFailed",
    "counterexample_from_failure",
    "raise_scenario_match_failure",
]
