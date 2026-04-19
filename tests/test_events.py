"""Tests for normalized event types."""

from dataclasses import replace

from agent_spec_kit import (
    AgentTurnEvent,
    BaseEvent,
    SubagentCallEvent,
    ToolCallEvent,
    new_event_id,
)


def test_base_event_defaults() -> None:
    e = BaseEvent()
    assert e.turn_index is None
    assert e.event_id is None
    assert e.parent_id is None
    assert e.source_path == ()
    assert e.metadata == {}


def test_tool_call_event_frozen_replace() -> None:
    t = ToolCallEvent(tool_name="x", args={"a": 1})
    t2 = replace(t, result="ok", event_id="e1")
    assert t2.tool_name == "x"
    assert t2.result == "ok"
    assert t2.event_id == "e1"


def test_agent_turn_event_fields() -> None:
    a = AgentTurnEvent(user_input="hi", agent_output="bye", turn_index=2)
    assert a.user_input == "hi"
    assert a.agent_output == "bye"
    assert a.turn_index == 2


def test_subagent_call_event_fields() -> None:
    s = SubagentCallEvent(agent_name="researcher", call_output="done")
    assert s.agent_name == "researcher"
    assert s.call_output == "done"


def test_new_event_id_prefix() -> None:
    a = new_event_id()
    b = new_event_id(prefix="p:")
    assert len(a) == 32
    assert b.startswith("p:")
