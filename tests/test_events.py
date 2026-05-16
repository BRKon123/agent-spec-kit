"""Tests for normalized event types."""

import pytest

from agent_spec_kit import (
    AgentTurnEvent,
    BaseEvent,
    ToolCallEvent,
    UserTurnEvent,
    collect_event_errors,
    new_event_id,
    print_rich_event_trace,
)


def test_base_event_defaults() -> None:
    e = BaseEvent()
    assert e.turn_index is None
    assert e.event_id is None
    assert e.source_path == ()
    assert e.metadata == {}
    assert e.children == []


def test_tool_call_event_mutable_children() -> None:
    t = ToolCallEvent(tool_name="x", args={"a": 1}, event_id="e1")
    inner = ToolCallEvent(tool_name="inner", event_id="e2")
    t.children.append(inner)
    assert t.children[0] is inner
    assert t.tool_name == "x"
    assert t.result is None


def test_agent_turn_event_fields() -> None:
    a = AgentTurnEvent(user_input="hi", agent_output="bye", turn_index=2)
    assert a.user_input == "hi"
    assert a.agent_output == "bye"
    assert a.turn_index == 2


def test_new_event_id_prefix() -> None:
    a = new_event_id()
    b = new_event_id(prefix="p:")
    assert len(a) == 32
    assert b.startswith("p:")


def test_rich_node_labels() -> None:
    assert BaseEvent()._rich_node_label() == "BaseEvent"
    assert ToolCallEvent(tool_name="t", result=1)._rich_node_label().startswith("t  result=")
    assert AgentTurnEvent(agent_output="pong")._rich_node_label() == "AgentTurn: pong"
    assert (
        AgentTurnEvent(source_path=("nested",), agent_output="pong")._rich_node_label()
        == "AgentTurn (nested): pong"
    )
    assert UserTurnEvent(content="ping")._rich_node_label() == "UserTurn: ping"


def test_collect_event_errors_nested_subgraph_and_tool() -> None:
    root = AgentTurnEvent(agent_output="ok")
    root.children.append(
        AgentTurnEvent(
            agent_output="",
            error="Failed to parse NetworkAssessment",
            source_path=("network_specialist",),
        )
    )
    root.children.append(ToolCallEvent(tool_name="demo", error="tool failed"))
    errs = collect_event_errors(root)
    assert errs == (
        "network_specialist: Failed to parse NetworkAssessment",
        "demo: tool failed",
    )


def test_print_rich_event_trace_smoke() -> None:
    pytest.importorskip("rich")
    from rich.console import Console

    root = AgentTurnEvent(user_input="hi", agent_output="bye")
    root.children.append(ToolCallEvent(tool_name="noop", result="ok"))
    print_rich_event_trace(Console(width=120), (root,), title="test trace")
