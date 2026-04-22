"""Structured scenario failures and counterexamples for reporting."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.match.types import MatchError, _short_repr
from agent_spec_kit.run import ConversationTurn

_MISSING = object()


def _window_conversation_for_trace(
    turns: tuple[ConversationTurn, ...], *, max_agent_turns: int = 5
) -> tuple[ConversationTurn, ...]:
    """Last ``max_agent_turns`` agent turns and their interleaved user lines (contiguous tail)."""
    if not turns:
        return ()
    agent_idx = [i for i, t in enumerate(turns) if t.actor == "agent"]
    if not agent_idx:
        return turns
    take = agent_idx[-max_agent_turns:]
    i_lo = min(take)
    while i_lo > 0 and turns[i_lo - 1].actor == "user":
        i_lo -= 1
    return turns[i_lo:]


def conversation_turns_to_event_trace(
    turns: Sequence[ConversationTurn], *, max_agent_turns: int = 5
) -> tuple[Any, ...]:
    """
    Build Rich tree roots for a failure panel: user lines as ``UserTurnEvent``,
    agent lines as each root in :attr:`ConversationTurn.events`, or a shell
    ``AgentTurnEvent`` when the turn has no event tree. At most the last
    ``max_agent_turns`` **agent** turns (with interleaved user turns).
    """
    from agent_spec_kit.events import AgentTurnEvent, UserTurnEvent

    win = _window_conversation_for_trace(tuple(turns), max_agent_turns=max_agent_turns)
    out: list[Any] = []
    for ct in win:
        if ct.actor == "user":
            out.append(UserTurnEvent(content=ct.output, error=ct.error))
        else:
            if ct.events:
                out.extend(ct.events)
            else:
                out.append(AgentTurnEvent(agent_output=ct.output, error=ct.error))
    return tuple(out)


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


def _deref_match_path(root: Any, path: tuple[Any, ...]) -> Any:
    """Follow ``path`` through dicts and lists; return ``_MISSING`` if traversal fails."""
    cur: Any = root
    for p in path:
        if isinstance(cur, list):
            if not isinstance(p, int) or p < 0 or p >= len(cur):
                return _MISSING
            cur = cur[p]
        elif isinstance(cur, dict):
            if not isinstance(p, str) or p not in cur:
                return _MISSING
            cur = cur[p]
        else:
            return _MISSING
    return cur


def _format_scenario_location(*, step_index: int, step_kind: str, turn_index: int | None) -> str:
    turn_part = ""
    if turn_index is not None:
        turn_part = f"after user message #{turn_index + 1}"
    else:
        turn_part = "before any completed user turn"
    labels = {
        "assert_output": "assert_output (final assistant text for that turn)",
        "assert_tool_calls": "assert_tool_calls (tool call list for that turn)",
        "assert_that": "assert_that (environment / fixture check)",
        "scenario_body": "scenario body (Python assert in test function)",
    }
    kind = labels.get(step_kind, step_kind)
    return f"Queued step {step_index} — {kind} — {turn_part}"


def _summarize_list_length_mismatch(
    err: MatchError, wit: dict[str, Any], record: FailureRecord
) -> tuple[str, str, list[str]]:
    notes: list[str] = []
    etn = wit.get("expected_tool_names")
    atn = wit.get("actual_tool_names")
    el = wit.get("expected_len")
    al = wit.get("actual_len")
    if isinstance(etn, list) and isinstance(atn, list) and isinstance(el, int) and isinstance(al, int):
        exp_line = (
            f"{err.code}: expected {el} tool call(s) in order: "
            f"{', '.join(str(x) for x in etn) if etn else '(none)'}"
        )
        act_line = (
            f"agent recorded {al} tool call(s): "
            f"{', '.join(str(x) for x in atn) if atn else '(none)'}"
        )
        notes.append(err.message)
        return exp_line, act_line, notes
    if isinstance(el, int) and isinstance(al, int):
        exp_line = f"{err.code}: expected {el} item(s) in list"
        act_line = f"got {al} item(s)"
        aw = wit.get("actual_witness")
        if aw is not None and (al > 0 or aw):
            try:
                act_line += f"\npreview: {_short(json.dumps(aw, default=str), 500)}"
            except TypeError:
                act_line += f"\npreview: {_short(repr(aw), 500)}"
        notes.append(err.message)
        return exp_line, act_line, notes
    return _short(f"{err.code}: expected {err.expected}", 200), str(wit.get("actual_witness", record.actual)), [err.message]


def _summarize_matcher_counterexample(record: FailureRecord, err: MatchError, wit: dict[str, Any]) -> tuple[str, str, list[str]]:
    notes: list[str] = []
    if err.code == "list_length_mismatch":
        return _summarize_list_length_mismatch(err, wit, record)

    path_s = _path_to_str(err.path)
    if path_s not in ("$", "()") and record.step_kind == "assert_tool_calls" and isinstance(record.actual, list):
        focused = _deref_match_path(record.actual, err.path)
        if focused is not _MISSING:
            exp_line = _short(f"{err.code}: expected {err.expected}", 200)
            act_line = f"At {path_s}: {_short_repr(focused)}"
            try:
                full = json.dumps(record.actual, indent=2, default=str)
            except TypeError:
                full = repr(record.actual)
            notes.append(f"Full tool-call list:\n{_short(full, 1200)}")
            notes.append(err.message)
            return exp_line, act_line, notes

    actual_min: Any = wit.get("actual_witness", record.actual)
    if isinstance(actual_min, (dict, list)):
        try:
            actual_str = json.dumps(actual_min, default=str, indent=2)
        except TypeError:
            actual_str = repr(actual_min)
    else:
        actual_str = str(actual_min)
    actual_str = _short(actual_str, 800)
    notes.append(err.message)
    return _short(f"{err.code}: expected {err.expected}", 200), actual_str, notes


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
    events: tuple[Any, ...] | None = None
    # When set, counterexample uses conversation_turns_to_event_trace (up to 5 recent agent turns).
    turn_results: tuple[ConversationTurn, ...] | None = None


@dataclass(slots=True)
class Counterexample:
    headline: str
    location: str
    path: str | None
    expected_summary: str
    actual_min: Any
    notes: tuple[str, ...] = ()
    check_kind: str | None = None
    location_detail: str | None = None
    events: tuple[Any, ...] | None = None


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


def _trace_events_for_record(record: FailureRecord) -> tuple[Any, ...] | None:
    if record.turn_results is not None and len(record.turn_results) > 0:
        return conversation_turns_to_event_trace(record.turn_results)
    return record.events


def _counterexample_base(
    *,
    headline: str,
    record: FailureRecord,
    path_s: str | None,
    expected_summary: str,
    actual_min: Any,
    notes: tuple[str, ...],
) -> Counterexample:
    loc = f"step {record.step_index}"
    if record.turn_index is not None:
        loc += f", turn {record.turn_index}"
    detail = _format_scenario_location(
        step_index=record.step_index,
        step_kind=record.step_kind,
        turn_index=record.turn_index,
    )
    return Counterexample(
        headline=headline,
        location=loc,
        path=path_s,
        expected_summary=expected_summary,
        actual_min=actual_min,
        notes=notes,
        check_kind=record.step_kind,
        location_detail=detail,
        events=_trace_events_for_record(record),
    )


def counterexample_from_failure(record: FailureRecord) -> Counterexample:
    """Build a counterexample from a failure record (matcher-first, display caps)."""
    if record.matcher_errors:
        err = record.matcher_errors[0]
        wit = _witness_dict(err)
        path_s = _path_to_str(err.path)
        exp_s, act_s, note_list = _summarize_matcher_counterexample(record, err, wit)
        if len(record.matcher_errors) > 1:
            note_list.append(f"(+{len(record.matcher_errors) - 1} more matcher error(s))")
        return _counterexample_base(
            headline=f"{record.scenario_name}: {err.message}",
            record=record,
            path_s=path_s,
            expected_summary=_short(exp_s, 600),
            actual_min=act_s,
            notes=tuple(note_list),
        )
    if record.error is not None:
        msg = str(record.error) or type(record.error).__name__
        headline = f"{record.scenario_name}: {msg}"
        if record.step_kind == "assert_that":
            exp = f"assert_that failed: {msg}" if msg else "assert_that failed"
        else:
            exp = msg if isinstance(record.error, AssertionError) and msg else type(record.error).__name__
        if record.step_kind == "assert_that" and record.actual in ((), None, False):
            if record.actual is False:
                act = "assert_that callable returned False (no further detail)."
            else:
                act = "No structured value compared (fixture/env assertion only — see message above)."
        elif record.actual in ((), None):
            act = "No structured value (see assertion message above)."
        else:
            act = _short(repr(record.actual), 400)
        return _counterexample_base(
            headline=headline,
            record=record,
            path_s=None,
            expected_summary=_short(exp, 500),
            actual_min=act,
            notes=(),
        )
    return _counterexample_base(
        headline=f"{record.scenario_name}: assertion failed",
        record=record,
        path_s=None,
        expected_summary="(no matcher errors)",
        actual_min=record.actual,
        notes=(),
    )


def _with_headline_prefix(cx: Counterexample, headline_prefix: str) -> Counterexample:
    return Counterexample(
        headline=f"{headline_prefix}: {cx.headline}",
        location=cx.location,
        path=cx.path,
        expected_summary=cx.expected_summary,
        actual_min=cx.actual_min,
        notes=cx.notes,
        check_kind=cx.check_kind,
        location_detail=cx.location_detail,
        events=cx.events,
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
    events: tuple[Any, ...] | None = None,
    turn_results: tuple[ConversationTurn, ...] | None = None,
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
        events=events,
        turn_results=turn_results,
    )
    cx = counterexample_from_failure(record)
    if headline_prefix:
        cx = _with_headline_prefix(cx, headline_prefix)
    raise ScenarioAssertionFailed(cx, record=record) from None


__all__ = [
    "Counterexample",
    "FailureRecord",
    "ScenarioAssertionFailed",
    "conversation_turns_to_event_trace",
    "counterexample_from_failure",
    "raise_scenario_match_failure",
]
