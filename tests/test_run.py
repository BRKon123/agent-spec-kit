"""Tests for TurnResult and AdaptedAgent."""

from agent_spec_kit import AgentTurnEvent, TurnResult


def test_turn_result_defaults() -> None:
    t = TurnResult(output="x", events=())
    assert t.status == "ok"
    assert t.error is None
    assert t.events == ()
