"""Tests for :meth:`Scenario.simulate_conversation` and mixing with ``user_message``."""

from __future__ import annotations

import asyncio

import pytest

import agent_spec_kit.match as m
from agent_spec_kit import create_scenario
from agent_spec_kit.run import TurnResult


def _run(c):
    return asyncio.run(c)


class _Scripted:
    def __init__(self, outputs: list[str]) -> None:
        self._i = 0
        self.outputs = outputs
        self.received: list[str] = []

    async def run_turn(self, user_message: str) -> TurnResult:
        self.received.append(user_message)
        if self._i >= len(self.outputs):
            return TurnResult(output="(done)", events=(), status="error", error="exhausted")
        o = self.outputs[self._i]
        self._i += 1
        return TurnResult(output=o, events=())


def test_user_message_after_simulate_allowed() -> None:
    a = _Scripted(["hi"])
    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="start", max_turns=1)
    s.user_message("x")
    _run(s.materialise())
    assert "x" in a.received


def test_simulate_after_user_message_allowed() -> None:
    a = _Scripted(["hi", "h2"])
    s = create_scenario(a)
    s.user_message("u")
    s.simulate_conversation(seed_actor="user", seed_input="s", max_turns=2)
    _run(s.materialise())
    assert len(a.received) >= 1


def test_first_simulate_requires_seed() -> None:
    a = _Scripted(["a"])
    s = create_scenario(a)
    s.simulate_conversation(max_turns=1)
    with pytest.raises(TypeError, match="seed"):
        _run(s.materialise())


def test_continuation_ignores_reseed() -> None:
    a = _Scripted(["a", "b", "c"])
    u = _Scripted(["u0", "u1"])
    s = create_scenario(a, user=u)
    s.simulate_conversation(seed_actor="user", seed_input="seed", max_turns=1)
    s.simulate_conversation(max_turns=1, seed_input="nope")
    _run(s.materialise())


def test_dual_user_seed_then_agent() -> None:
    a = _Scripted(["agent1", "agent2"])
    u = _Scripted(["user_visible"])
    s = create_scenario(a, user=u)
    s.simulate_conversation(seed_actor="user", seed_input="hidden", max_turns=2)
    _run(s.materialise())
    assert u.received[0] == "hidden"
    assert a.received[0] == "user_visible"
    assert len(s.turn_results) == 2
    assert s.turn_results[0].actor == "user"
    assert s.turn_results[0].output == "user_visible"
    assert s.turn_results[1].actor == "agent"
    assert s.last_turn.output == "agent1"


def test_interleaved_assert_then_continuation() -> None:
    a = _Scripted(["A1", "A2", "A3"])
    u = _Scripted(["U1", "U2"])
    s = create_scenario(a, user=u)
    # max_turns counts utterances; stop after one user line in segment 1
    s.simulate_conversation(
        seed_actor="user",
        seed_input="h1",
        max_turns=3,
        stop_condition=m.contains("U1"),
    )
    s.assert_output(m.contains("U1"), actor="user")
    # One full round in segment 2, stop after the agent so we do not add a user reply
    s.simulate_conversation(max_turns=1, stop_condition=m.contains("A1"))
    _run(s.materialise())
    assert len(s.turn_results) == 2
    assert a.received[0] == "U1"


def test_assert_output_defaults_to_last_speaker() -> None:
    a = _Scripted(["A1"])
    u = _Scripted(["U1"])
    s = create_scenario(a, user=u)
    s.simulate_conversation(seed_actor="user", seed_input="h", max_turns=2)
    s.assert_output(m.contains("A1"))
    _run(s.materialise())
