"""Mixing user_message, simulate_conversation, and fuzz_conversation; joint fuzz trials."""

from __future__ import annotations

import asyncio

import pytest

from agent_spec_kit.decorators import fixture, scenario
from agent_spec_kit.fuzz.behaviour_grammar import behaviour_grammar
from agent_spec_kit.fuzz_config import FuzzConfig, UserAction
from agent_spec_kit.registries import iter_scenarios, reset_registries
from agent_spec_kit.runner import run_scenario_job
from agent_spec_kit.run import TurnResult

_FC = FuzzConfig(
    strategy=behaviour_grammar((UserAction(name="one", templates=("zz",)),)),
    seed=7,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_registries()
    yield
    reset_registries()


def test_user_message_then_simulate_resumes() -> None:
    @fixture
    async def agent():
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="agent-reply", events=())

        return A()

    @fixture
    async def user():
        class U:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="user-reply", events=())

        return U()

    @scenario(agent_fixture="agent", user_fixture="user", tags=())
    async def mix_sim(s):  # type: ignore[no-untyped-def]
        (
            s.user_message("hello")
            .simulate_conversation(seed_actor="agent", seed_input="go", max_turns=2)
        )

    sd = next(s for s in iter_scenarios() if s.name == "mix_sim")
    r = asyncio.run(run_scenario_job(sd, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail


def test_user_message_then_fuzz_joint_trials() -> None:
    @fixture
    async def agent():
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="ok", events=())

        return A()

    @fixture
    async def user():
        class U:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="u", events=())

        return U()

    @scenario(agent_fixture="agent", user_fixture="user", tags=())
    async def mix_fuzz(s):  # type: ignore[no-untyped-def]
        (
            s.user_message("setup")
            .fuzz_conversation(fuzz_config=_FC, trials=3, max_user_turns=1)
        )

    sd = next(s for s in iter_scenarios() if s.name == "mix_fuzz")
    r = asyncio.run(run_scenario_job(sd, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail
    assert len(r.fuzz_trials) == 3


def test_two_fuzz_steps_mismatched_trials_phase_error() -> None:
    fc2 = FuzzConfig(strategy=_FC.strategy, seed=8)

    @fixture
    async def agent():
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="ok", events=())

        return A()

    @fixture
    async def user():
        class U:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="u", events=())

        return U()

    @scenario(agent_fixture="agent", user_fixture="user", tags=())
    async def fuzz_mismatch(s):  # type: ignore[no-untyped-def]
        (
            s.fuzz_conversation(fuzz_config=_FC, trials=2, max_user_turns=1)
            .fuzz_conversation(fuzz_config=fc2, trials=3, max_user_turns=1)
        )

    sd = next(s for s in iter_scenarios() if s.name == "fuzz_mismatch")
    r = asyncio.run(run_scenario_job(sd, repeat_index=1, repeat_total=1))
    assert not r.ok
    assert r.phase_errors
    assert any(e.get("error_kind") == "FuzzTrialsMismatch" for e in r.phase_errors)


def test_two_fuzz_steps_joint_per_step_breakdown() -> None:
    fc2 = FuzzConfig(strategy=_FC.strategy, seed=9)

    @fixture
    async def agent():
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="ok", events=())

        return A()

    @fixture
    async def user():
        class U:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="u", events=())

        return U()

    @scenario(agent_fixture="agent", user_fixture="user", tags=())
    async def fuzz_joint(s):  # type: ignore[no-untyped-def]
        (
            s.fuzz_conversation(fuzz_config=_FC, trials=2, max_user_turns=1)
            .fuzz_conversation(fuzz_config=fc2, trials=2, max_user_turns=1)
        )

    sd = next(s for s in iter_scenarios() if s.name == "fuzz_joint")
    r = asyncio.run(run_scenario_job(sd, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail
    assert len(r.fuzz_trials) == 2
    for ft in r.fuzz_trials:
        pst = ft.get("per_step_user_turns")
        assert pst is not None
        assert len(pst) == 2
        assert len(pst[0]) == 1
        assert len(pst[1]) == 1
