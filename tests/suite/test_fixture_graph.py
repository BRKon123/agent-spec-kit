"""Fixture graph resolution and teardown order."""

from __future__ import annotations

import asyncio

import pytest

from agent_spec_kit.decorators import fixture, scenario
from agent_spec_kit.fixture_graph import resolve_fixtures
from agent_spec_kit.registries import iter_scenarios, reset_registries
from agent_spec_kit.runner import run_scenario_job


def test_fixture_cycle_error() -> None:
    reset_registries()

    @fixture
    def a(b):  # type: ignore[no-untyped-def]
        return 1

    @fixture
    def b(a):  # type: ignore[no-untyped-def]
        return 2

    @scenario(agent_fixture="a", tags=())
    async def t(s):  # type: ignore[no-untyped-def]
        pass

    sd = next(s for s in iter_scenarios() if s.name == "t")

    async def run() -> None:
        await resolve_fixtures(sd)

    with pytest.raises(RuntimeError, match="cycle"):
        asyncio.run(run())


def test_teardown_reverse_order() -> None:
    reset_registries()
    log: list[str] = []

    @fixture
    def inner():
        log.append("inner+")
        yield 1
        log.append("inner-")

    @fixture
    def outer(inner):  # type: ignore[no-untyped-def]
        log.append("outer+")
        yield 2
        log.append("outer-")

    @fixture
    async def agent(inner, outer):  # type: ignore[no-untyped-def]
        from agent_spec_kit.run import TurnResult

        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="ok", events=())

        return A()

    @scenario(agent_fixture="agent", tags=())
    async def t(s, inner, outer):  # type: ignore[no-untyped-def]
        assert inner == 1 and outer == 2

    sd = next(s for s in iter_scenarios() if s.name == "t")
    r = asyncio.run(run_scenario_job(sd, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail
    assert log == ["inner+", "outer+", "outer-", "inner-"]


def test_auto_materialise_pending_steps() -> None:
    reset_registries()

    @fixture
    async def agent():
        from agent_spec_kit.run import TurnResult

        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="done", events=())

        return A()

    @scenario(agent_fixture="agent", tags=())
    async def auto_mat(s):  # type: ignore[no-untyped-def]
        s.user_message("hi")

    sd = next(s for s in iter_scenarios() if s.name == "auto_mat")
    r = asyncio.run(run_scenario_job(sd, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail
