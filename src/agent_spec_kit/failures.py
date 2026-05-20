"""Structured scenario failures and counterexamples for reporting."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from agent_spec_kit.match.types import MatchError, MatchResult, _short_repr, path_to_str
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


def _flatten_root_agent_shells(nodes: Iterable[Any]) -> list[Any]:
    """
    Drop nested ``AgentTurnEvent`` wrappers that still have ``source_path == ()``.

    LangGraph sometimes emits an extra root-shaped ``AgentTurnEvent`` between the
    outer turn and ``ToolCallEvent`` nodes; a single-level promotion still left
    ``UserTurn -> AgentTurn (root) -> tool``. Recurse until only meaningful nodes
    (tools, subgraph ``AgentTurnEvent`` with non-empty ``source_path``, etc.) remain.
    """
    from agent_spec_kit.events import AgentTurnEvent

    out: list[Any] = []
    for n in nodes:
        if isinstance(n, AgentTurnEvent) and n.source_path == ():
            out.extend(_flatten_root_agent_shells(n.children))
        else:
            out.append(n)
    return out


def _children_for_user_turn_trace(events: tuple[Any, ...]) -> list[Any]:
    """
    Map ``ConversationTurn.events`` for a user line into Rich children for ``UserTurnEvent``.

    A wrapped LangChain / Pydantic user turn is often a single root ``AgentTurnEvent``
    (``source_path == ()``). For traces we splice its (nested) shell's children so
    ``student_checkpoint`` (etc.) sit directly under the user line, not under one
    or more redundant ``AgentTurn (root)`` nodes. Non-root subgraph turns keep their
    ``AgentTurn`` node (non-empty ``source_path``).
    """
    from agent_spec_kit.events import AgentTurnEvent

    if len(events) == 1 and isinstance(events[0], AgentTurnEvent):
        root = events[0]
        if root.source_path == ():
            return _flatten_root_agent_shells(root.children)
    return list(events)


def conversation_turns_to_event_trace(
    turns: Sequence[ConversationTurn], *, max_agent_turns: int = 5
) -> tuple[Any, ...]:
    """
    Build Rich tree roots for a failure panel: user lines as ``UserTurnEvent``,
    agent lines as each root in :attr:`ConversationTurn.events`, or a shell
    ``AgentTurnEvent`` when the turn has no event tree. At most the last
    ``max_agent_turns`` **agent** turns (with interleaved user turns).

    ``UserTurnEvent`` and ``AgentTurnEvent`` roots stay **siblings** in turn order.
    User-side ``ConversationTurn.events`` become ``UserTurnEvent.children``. If there
    is exactly one root ``AgentTurnEvent`` with ``source_path == ()`` (typical adapter
    shell), nested same-path shells are stripped recursively so tools appear directly
    under the user line.
    """
    from agent_spec_kit.events import AgentTurnEvent, UserTurnEvent

    win = _window_conversation_for_trace(tuple(turns), max_agent_turns=max_agent_turns)
    out: list[Any] = []
    for ct in win:
        if ct.actor == "user":
            ue = UserTurnEvent(content=ct.output, error=ct.error)
            ue.children.extend(_children_for_user_turn_trace(ct.events))
            out.append(ue)
        else:
            if ct.events:
                out.extend(ct.events)
            else:
                out.append(AgentTurnEvent(agent_output=ct.output, error=ct.error))
    return tuple(out)


def _short(s: str, max_len: int = 400) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _format_actual_value(value: Any) -> str:
    """Serialize ``value`` for display without length caps (UI scrolls)."""
    if isinstance(value, (dict, list, tuple)):
        try:
            payload = list(value) if isinstance(value, tuple) else value
            return json.dumps(payload, default=str, indent=2)
        except TypeError:
            return repr(value)
    return str(value)


def collect_agent_errors(
    *,
    actual: Any = None,
    events: tuple[Any, ...] | None = None,
    turn_results: tuple[ConversationTurn, ...] | None = None,
) -> tuple[str, ...]:
    """Collect non-empty agent/tool error strings for failure panels (full text, deduped)."""
    from agent_spec_kit.events import collect_event_errors

    found: list[str] = []

    def add(msg: str) -> None:
        text = msg.strip()
        if text and text not in found:
            found.append(text)

    if isinstance(actual, (list, tuple)):
        for item in actual:
            add(str(item))
    elif isinstance(actual, str):
        stripped = actual.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                for item in parsed:
                    add(str(item))
            else:
                add(actual)
        else:
            add(actual)
    elif actual not in ((), None):
        add(str(actual))

    trace_events = events
    if trace_events is None and turn_results:
        trace_events = conversation_turns_to_event_trace(turn_results)
    if trace_events:
        for root in trace_events:
            for err in collect_event_errors(root):
                add(err)

    return tuple(found)


def _should_prepend_act_summary_to_notes(
    act_summary: str, record: FailureRecord, actual_min: Any
) -> bool:
    """Skip JSON dumps in notes when Actual already shows the full tool-call list."""
    if not act_summary.strip():
        return False
    if record.step_kind == "assert_tool_calls" and isinstance(actual_min, list):
        stripped = act_summary.lstrip()
        if stripped.startswith(("[", "{")):
            return False
    return True


def _counterexample_actual(
    record: FailureRecord,
    err: MatchError | None,
    wit: dict[str, Any],
) -> Any:
    """Full actual payload for counterexample panels (no truncation)."""
    if record.step_kind == "assert_tool_calls" and isinstance(record.actual, list):
        return record.actual
    aw = wit.get("actual_witness")
    if aw is not None:
        return aw
    if isinstance(record.actual, (dict, list)):
        return record.actual
    return _format_actual_value(record.actual)


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


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _format_scenario_location(
    *,
    step_kind: str,
    turn_index: int | None,
    assertion_index_after_turn: int | None,
    turn_actor: str | None,
) -> str:
    labels = {
        "assert_output": (
            "assert_output",
            "(final assistant text for that turn)",
        ),
        "assert_tool_calls": (
            "assert_tool_calls",
            "(tool call list for that turn)",
        ),
        "forbid_tool_calls": (
            "forbid_tool_calls",
            "(forbidden tool call patterns)",
        ),
        "assert_that": ("assert_that", "(environment / fixture check)"),
        "scenario_body": ("scenario body", "(Python assert in test function)"),
        "agent_error": ("agent error", "(runtime error during agent execution)"),
    }
    kind_base, kind_suffix = labels.get(step_kind, (step_kind, ""))
    kind = kind_base
    if assertion_index_after_turn is not None and assertion_index_after_turn > 0:
        kind = f"{_ordinal(assertion_index_after_turn)} {kind}"
    if turn_index is None:
        suffix = f" {kind_suffix}" if kind_suffix else ""
        return f"{kind} before any completed user turn{suffix}"
    role = f" ({turn_actor}turn)" if turn_actor in {"agent", "user"} else ""
    suffix = f" {kind_suffix}" if kind_suffix else ""
    return f"{kind} after turn #{turn_index + 1}{role}{suffix}"


def _turn_actor_for_record(record: FailureRecord) -> str | None:
    if record.turn_index is None or record.turn_results is None:
        return None
    if record.turn_index < 0 or record.turn_index >= len(record.turn_results):
        return None
    actor = record.turn_results[record.turn_index].actor
    return actor if isinstance(actor, str) else None


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

    path_s = path_to_str(err.path)
    if path_s not in ("$", "()") and record.step_kind == "assert_tool_calls" and isinstance(record.actual, list):
        focused = _deref_match_path(record.actual, err.path)
        if focused is not _MISSING:
            exp_line = _short(f"{err.code}: expected {err.expected}", 200)
            notes.append(err.message)
            return exp_line, "", notes

    actual_min: Any = wit.get("actual_witness", record.actual)
    notes.append(err.message)
    return _short(f"{err.code}: expected {err.expected}", 200), _format_actual_value(actual_min), notes


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
    assertion_index_after_turn: int | None = None


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
        step_kind=record.step_kind,
        turn_index=record.turn_index,
        assertion_index_after_turn=record.assertion_index_after_turn,
        turn_actor=_turn_actor_for_record(record),
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
        outer_err = record.matcher_errors[0]
        err = max(record.matcher_errors, key=lambda e: len(e.path))
        wit = _witness_dict(err)
        path_s = path_to_str(err.path)
        exp_s, act_summary, note_list = _summarize_matcher_counterexample(record, err, wit)
        if err is not outer_err:
            note_list.insert(0, outer_err.message)
        if len(record.matcher_errors) > 1:
            note_list.append(f"(+{len(record.matcher_errors) - 1} more matcher error(s))")
        if err is not outer_err:
            headline_message = f"{outer_err.message}; mismatch at {path_s}: {err.message}"
        else:
            headline_message = err.message
        actual_min_val = _counterexample_actual(record, err, wit)
        notes_final = list(note_list)
        if _should_prepend_act_summary_to_notes(act_summary, record, actual_min_val):
            notes_final.insert(0, act_summary)
        return _counterexample_base(
            headline=f"{record.scenario_name}: {headline_message}",
            record=record,
            path_s=path_s,
            expected_summary=_short(exp_s, 600),
            actual_min=actual_min_val,
            notes=tuple(notes_final),
        )
    if record.error is not None:
        msg = str(record.error) or type(record.error).__name__
        headline = f"{record.scenario_name}: {msg}"
        if record.step_kind == "assert_that":
            exp = f"assert_that failed: {msg}" if msg else "assert_that failed"
        elif record.step_kind == "agent_error":
            exp = "agent turn completes without runtime errors"
        else:
            exp = msg if isinstance(record.error, AssertionError) and msg else type(record.error).__name__
        if record.step_kind == "agent_error":
            errs = collect_agent_errors(
                actual=record.actual,
                events=_trace_events_for_record(record),
                turn_results=record.turn_results,
            )
            act = list(errs) if errs else "No structured value (see assertion message above)."
        elif record.step_kind == "assert_that" and record.actual in ((), None, False):
            if record.actual is False:
                act = "assert_that callable returned False (no further detail)."
            else:
                act = "No structured value compared (fixture/env assertion only — see message above)."
        elif record.actual in ((), None):
            act = "No structured value (see assertion message above)."
        else:
            act = _format_actual_value(record.actual)
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
    assertion_index_after_turn: int | None = None,
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
        assertion_index_after_turn=assertion_index_after_turn,
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
    "collect_agent_errors",
    "counterexample_from_failure",
    "raise_scenario_match_failure",
]
