"""Counterexample and structured failure types."""

from __future__ import annotations

import agent_spec_kit.match as m
from agent_spec_kit.match.api import tool_call
from agent_spec_kit.run import ConversationTurn, TurnResult
from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.failures import (
    FailureRecord,
    ScenarioAssertionFailed,
    collect_agent_errors,
    conversation_turns_to_event_trace,
    counterexample_from_failure,
    raise_scenario_match_failure,
)


def test_counterexample_from_match_error() -> None:
    r = m.check(m.list([1, 2]), [1])
    assert not r.ok
    record = FailureRecord(
        scenario_name="t_example",
        step_index=2,
        step_kind="assert_tool_calls",
        turn_index=0,
        actual=[{"name": "x"}],
        matcher_spec=[1, 2],
        matcher_errors=r.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    assert "t_example" in cx.headline
    assert "step 2" in cx.location
    assert cx.path is not None


def test_counterexample_list_length_tool_calls_shows_counts_and_names() -> None:
    r = m.check(m.list([tool_call("a"), tool_call("b")], mode="ordered"), [{"name": "a"}])
    assert not r.ok
    record = FailureRecord(
        scenario_name="t_tools",
        step_index=1,
        step_kind="assert_tool_calls",
        turn_index=0,
        actual=[{"name": "a", "args": {}, "result": "1", "error": None, "children": [], "metadata": {}}],
        matcher_spec=[tool_call("a"), tool_call("b")],
        matcher_errors=r.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    assert "expected 2 tool call" in cx.expected_summary or "2" in cx.expected_summary
    assert "a" in cx.expected_summary and "b" in cx.expected_summary
    assert any("agent recorded 1" in n for n in cx.notes)
    assert isinstance(cx.actual_min, list) and len(cx.actual_min) == 1
    assert cx.check_kind == "assert_tool_calls"


def test_counterexample_tool_calls_notes_skip_truncated_json_preview() -> None:
    """Notes must not prepend a truncated ``actual_witness`` JSON blob when Actual has the full list."""
    spec = m.list([m.object({"args": {"window_minutes": 30}})], allow_extras=True)
    actual = [
        {
            "name": "open_incident",
            "args": {"severity": "high"},
            "result": "ok",
            "error": None,
            "children": [
                {
                    "name": "pull_logs",
                    "args": {"source": "edge"},
                    "result": "logs",
                    "error": None,
                    "children": [
                        {
                            "name": "score_anomaly",
                            "args": {"source": "edge", "anomaly_score": 0.72, "window_minutes": 15},
                            "result": "scored",
                            "error": None,
                            "children": [],
                            "metadata": {},
                        }
                    ],
                    "metadata": {},
                }
            ],
            "metadata": {},
        }
    ]
    r = m.check(spec, actual)
    assert not r.ok
    record = FailureRecord(
        scenario_name="t_nested",
        step_index=1,
        step_kind="assert_tool_calls",
        turn_index=0,
        actual=actual,
        matcher_spec=spec,
        matcher_errors=r.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    assert isinstance(cx.actual_min, list)
    assert len(cx.actual_min) == 1
    notes_joined = "\n".join(cx.notes)
    assert not notes_joined.lstrip().startswith("[")
    assert not notes_joined.lstrip().startswith("{")


def test_counterexample_tool_call_mismatch_notes_do_not_repeat_full_list() -> None:
    r = m.check(m.list([1], allow_extras=True), [2])
    assert not r.ok
    record = FailureRecord(
        scenario_name="t_tools_mismatch",
        step_index=1,
        step_kind="assert_tool_calls",
        turn_index=0,
        actual=[2],
        matcher_spec=[1],
        matcher_errors=r.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    notes_joined = "\n".join(cx.notes)
    assert "could not match expected element at index" in notes_joined
    assert "full tool-call list" not in notes_joined.lower()


def test_counterexample_uses_deepest_inner_path_for_tool_call_mismatch() -> None:
    spec = m.list([m.object({"args": {"a": 7}})], allow_extras=True)
    actual = [
        {
            "name": "multiply_integers",
            "args": {"a": 6, "b": 7},
            "result": "42",
            "error": None,
            "children": [],
            "metadata": {"tool_call_id": "call_1"},
        }
    ]
    r = m.check(spec, actual)
    assert not r.ok
    record = FailureRecord(
        scenario_name="t_deep_path",
        step_index=1,
        step_kind="assert_tool_calls",
        turn_index=0,
        actual=actual,
        matcher_spec=spec,
        matcher_errors=r.errors,
        error=None,
    )
    cx = counterexample_from_failure(record)
    assert cx.path == "$[0].args.a"
    assert "mismatch at $[0].args.a" in cx.headline
    assert isinstance(cx.actual_min, list)
    assert cx.actual_min[0]["metadata"]["tool_call_id"] == "call_1"


def test_counterexample_assert_that_uses_message_not_empty_tuple() -> None:
    record = FailureRecord(
        scenario_name="t_env",
        step_index=1,
        step_kind="assert_that",
        turn_index=0,
        actual=(),
        matcher_spec=None,
        matcher_errors=(),
        error=AssertionError("fixture X must be False"),
    )
    cx = counterexample_from_failure(record)
    assert "assert_that failed" in cx.expected_summary
    assert "fixture X" in cx.expected_summary
    assert "()" not in cx.actual_min
    assert "structured" in cx.actual_min.lower() or "fixture" in cx.actual_min.lower()


def test_counterexample_location_detail_includes_assertion_index_after_turn() -> None:
    turns = (ConversationTurn(actor="agent", output="out", error=None, events=()),)
    record = FailureRecord(
        scenario_name="t_location",
        step_index=3,
        step_kind="assert_output",
        turn_index=0,
        actual="actual",
        matcher_spec=None,
        matcher_errors=(),
        error=AssertionError("mismatch"),
        turn_results=turns,
        assertion_index_after_turn=2,
    )
    cx = counterexample_from_failure(record)
    assert (
        cx.location_detail
        == "2nd assert_output after turn #1 (agentturn) (final assistant text for that turn)"
    )


def test_raise_scenario_match_failure_raises_subclass() -> None:
    r = m.check(m.list([1]), [2])
    assert not r.ok
    try:
        raise_scenario_match_failure(
            scenario_name="s",
            step_index=0,
            step_kind="assert_output",
            turn_index=0,
            result=r,
            matcher_spec=1,
            actual=2,
            headline_prefix="assert_output",
        )
    except ScenarioAssertionFailed as e:
        assert e.counterexample.headline.startswith("assert_output:")
        assert e.record is not None
    else:
        raise AssertionError("expected ScenarioAssertionFailed")


def test_conversation_trace_includes_user_and_last_two_agent_turns() -> None:
    u0 = TurnResult(output="u0", events=())
    a0 = TurnResult(
        output="a0 out",
        events=(AgentTurnEvent(user_input="u0", agent_output="a0 out", children=[ToolCallEvent(tool_name="t0", result=0)]),),
    )
    u1 = TurnResult(output="u1", events=())
    a1 = TurnResult(
        output="a1 out",
        events=(AgentTurnEvent(user_input="u1", agent_output="a1 out", children=[ToolCallEvent(tool_name="t1", result=1)]),),
    )
    turns = (
        ConversationTurn.from_turn("user", u0),
        ConversationTurn.from_turn("agent", a0),
        ConversationTurn.from_turn("user", u1),
        ConversationTurn.from_turn("agent", a1),
    )
    roots = conversation_turns_to_event_trace(turns, max_agent_turns=5)
    assert len(roots) == 4
    from agent_spec_kit.events import UserTurnEvent

    assert isinstance(roots[0], UserTurnEvent) and roots[0].content == "u0"
    assert isinstance(roots[1], AgentTurnEvent)
    assert isinstance(roots[1].children[0], ToolCallEvent)
    assert roots[1].children[0].tool_name == "t0"
    assert isinstance(roots[2], UserTurnEvent) and roots[2].content == "u1"
    assert isinstance(roots[3], AgentTurnEvent)
    assert isinstance(roots[3].children[0], ToolCallEvent)
    assert roots[3].children[0].tool_name == "t1"


def test_conversation_trace_user_turn_attaches_events_as_children() -> None:
    """User-side TurnResult.events appear under UserTurnEvent.children; siblings stay user then agent."""
    from agent_spec_kit.events import UserTurnEvent

    u_tool = TurnResult(
        output="student line",
        events=(ToolCallEvent(tool_name="student_checkpoint", result="ok"),),
    )
    u_wrapped = TurnResult(
        output="wrapped student",
        events=(
            AgentTurnEvent(
                user_input="seed",
                agent_output="wrapped student",
                children=[ToolCallEvent(tool_name="inner_tool", result=99)],
            ),
        ),
    )
    a0 = TurnResult(
        output="tutor out",
        events=(AgentTurnEvent(agent_output="tutor out", children=[ToolCallEvent(tool_name="tutor_t", result=0)]),),
    )
    turns = (
        ConversationTurn.from_turn("user", u_tool),
        ConversationTurn.from_turn("agent", a0),
        ConversationTurn.from_turn("user", u_wrapped),
    )
    roots = conversation_turns_to_event_trace(turns, max_agent_turns=5)
    assert len(roots) == 3
    assert isinstance(roots[0], UserTurnEvent) and roots[0].content == "student line"
    assert len(roots[0].children) == 1
    assert isinstance(roots[0].children[0], ToolCallEvent)
    assert roots[0].children[0].tool_name == "student_checkpoint"
    assert isinstance(roots[1], AgentTurnEvent)
    assert isinstance(roots[1].children[0], ToolCallEvent)
    assert roots[1].children[0].tool_name == "tutor_t"
    assert isinstance(roots[2], UserTurnEvent) and roots[2].content == "wrapped student"
    assert len(roots[2].children) == 1
    assert isinstance(roots[2].children[0], ToolCallEvent)
    assert roots[2].children[0].tool_name == "inner_tool"


def test_conversation_trace_user_turn_flattens_nested_root_agent_shells() -> None:
    """Nested AgentTurnEvent(root) wrappers under the user root are stripped for traces."""
    from agent_spec_kit.events import UserTurnEvent

    inner = AgentTurnEvent(
        agent_output="inner",
        children=[ToolCallEvent(tool_name="student_checkpoint", result="first")],
    )
    root = AgentTurnEvent(agent_output="out", children=[inner])
    u = TurnResult(output="What is 4 times 5?", events=(root,))
    roots = conversation_turns_to_event_trace(
        (ConversationTurn.from_turn("user", u),),
        max_agent_turns=5,
    )
    assert len(roots) == 1 and isinstance(roots[0], UserTurnEvent)
    assert len(roots[0].children) == 1
    assert isinstance(roots[0].children[0], ToolCallEvent)
    assert roots[0].children[0].tool_name == "student_checkpoint"


def test_conversation_trace_user_turn_keeps_non_root_agent_as_child() -> None:
    """Single AgentTurn with non-empty source_path is not promoted (unusual on user)."""
    from agent_spec_kit.events import UserTurnEvent

    u_ns = TurnResult(
        output="x",
        events=(
            AgentTurnEvent(
                agent_output="x",
                source_path=("sub",),
                children=[ToolCallEvent(tool_name="t_ns", result=1)],
            ),
        ),
    )
    roots = conversation_turns_to_event_trace(
        (ConversationTurn.from_turn("user", u_ns),),
        max_agent_turns=5,
    )
    assert len(roots) == 1 and isinstance(roots[0], UserTurnEvent)
    assert len(roots[0].children) == 1
    assert isinstance(roots[0].children[0], AgentTurnEvent)
    assert roots[0].children[0].source_path == ("sub",)


def test_conversation_trace_scripted_user_message_emits_user_then_agent() -> None:
    """When ``s.user_message(...)`` synthesizes an actor=user ConversationTurn
    with no events, the failure trace shows a ``UserTurnEvent`` followed by the
    agent's ``AgentTurnEvent`` root — matching how console renders user turns."""
    from agent_spec_kit.events import UserTurnEvent

    user_ct = ConversationTurn(actor="user", output="Compute (4*5)+3.")
    agent_tr = TurnResult(
        output="answer",
        events=(
            AgentTurnEvent(
                user_input="Compute (4*5)+3.",
                agent_output="answer",
                children=[ToolCallEvent(tool_name="multiply_numbers", result=20)],
            ),
        ),
    )
    turns = (user_ct, ConversationTurn.from_turn("agent", agent_tr))
    roots = conversation_turns_to_event_trace(turns, max_agent_turns=5)
    assert len(roots) == 2
    assert isinstance(roots[0], UserTurnEvent)
    assert roots[0].content == "Compute (4*5)+3."
    assert roots[0].children == []
    assert isinstance(roots[1], AgentTurnEvent)
    assert roots[1].agent_output == "answer"
    assert isinstance(roots[1].children[0], ToolCallEvent)
    assert roots[1].children[0].tool_name == "multiply_numbers"


def test_conversation_trace_windows_last_five_agent_turns() -> None:
    """Earlier agent+user pair is dropped when more than 5 agent turns are present."""
    parts: list[ConversationTurn] = []
    for i in range(6):
        u = TurnResult(output=f"u{i}", events=())
        a = TurnResult(
            output=f"a{i}",
            events=(AgentTurnEvent(user_input=f"u{i}", agent_output=f"a{i}"),),
        )
        parts.append(ConversationTurn.from_turn("user", u))
        parts.append(ConversationTurn.from_turn("agent", a))
    roots = conversation_turns_to_event_trace(parts, max_agent_turns=5)
    from agent_spec_kit.events import UserTurnEvent

    user_contents = [r.content for r in roots if isinstance(r, UserTurnEvent)]
    # Oldest full round (u0, a0) is dropped; window starts with u1.
    assert "u0" not in user_contents
    assert "u1" in user_contents
    assert "u5" in user_contents


def test_collect_agent_errors_from_events_and_actual() -> None:
    root = AgentTurnEvent(agent_output="x", error="root parse failed")
    root.children.append(
        AgentTurnEvent(
            agent_output="",
            error="nested specialist failed",
            source_path=("network_specialist",),
        )
    )
    errs = collect_agent_errors(actual=("root parse failed",), events=(root,))
    assert errs == ("root parse failed", "network_specialist: nested specialist failed")


def test_counterexample_agent_error_expected_and_actual() -> None:
    err = "Failed to parse NetworkAssessment"
    record = FailureRecord(
        scenario_name="t",
        step_index=0,
        step_kind="agent_error",
        turn_index=0,
        actual=(err,),
        matcher_spec=None,
        matcher_errors=(),
        error=AssertionError(err),
    )
    cx = counterexample_from_failure(record)
    assert cx.expected_summary == "agent turn completes without runtime errors"
    assert err in (cx.actual_min if isinstance(cx.actual_min, str) else "\n".join(map(str, cx.actual_min)))
