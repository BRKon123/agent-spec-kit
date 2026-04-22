"""Integration tests for @parametrize and graph expansion."""

from __future__ import annotations

import asyncio

import agent_spec_kit as ek
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.registries import iter_scenarios, reset_registries
from agent_spec_kit.run import TurnResult
from agent_spec_kit.runner import run_scenario_job


def test_cartesian_two_axes() -> None:
    reset_registries()

    # @ek.fixture is outer: registration sees parametrize layers on the function first.
    @ek.fixture
    @ek.parametrize("a", [ek.case(1, id="a1"), ek.case(2, id="a2")])
    @ek.parametrize("b", [ek.case(10, id="b1"), ek.case(20, id="b2")])
    def base(a, b):  # type: ignore[no-untyped-def]
        return a * 1000 + b

    @ek.fixture
    async def agent(base):  # type: ignore[no-untyped-def]
        _ = base

        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="ok", events=())

        return A()

    @ek.scenario(agent_fixture="agent", tags=())
    async def t(s):  # type: ignore[no-untyped-def]
        _ = s.param("a")
        _ = s.param("b")
        assert s.case("a").id in ("a1", "a2")
        assert s.case("b").id in ("b1", "b2")

    sd = next(s for s in iter_scenarios() if s.name == "t")
    runs = scenario_case_runs(sd)
    assert len(runs) == 4
    for i, _r in enumerate(runs):
        res = asyncio.run(run_scenario_job(sd, case_index=i, repeat_index=1, repeat_total=1))
        assert res.ok, res.detail


def test_param_reachable_not_in_scenario_signature() -> None:
    """Axis `color` is only on the agent chain, not a scenario parameter."""
    reset_registries()

    @ek.fixture
    def store():  # type: ignore[no-untyped-def]
        return object()

    @ek.fixture
    @ek.parametrize("color", [ek.case("red", id="red"), ek.case("blue", id="blue")])
    def agent(color):  # type: ignore[no-untyped-def]
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output=color, events=())

        return A()

    @ek.scenario(agent_fixture="agent", tags=())
    async def t(s, store):  # type: ignore[no-untyped-def]  # noqa: ARG001
        assert s.param("color") in ("red", "blue")
        assert s.case("color").id in ("red", "blue")

    sd = next(s for s in iter_scenarios() if s.name == "t")
    runs = scenario_case_runs(sd)
    assert len(runs) == 2
    for i in range(2):
        r = asyncio.run(run_scenario_job(sd, case_index=i, repeat_index=1, repeat_total=1))
        assert r.ok, r.detail


def test_scenario_function_gets_injected_value_and_full_case() -> None:
    """``axis`` → Case.value, ``axis_case`` → Case (same as ``s.param`` / ``s.case``)."""
    reset_registries()

    @ek.fixture
    def store():  # type: ignore[no-untyped-def]
        return object()

    @ek.fixture
    @ek.parametrize("m", [ek.case("m1", id="m1id", meta={"k": 1})])
    def agent(m):  # type: ignore[no-untyped-def]
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="o", events=())

        return A()

    @ek.scenario(agent_fixture="agent", tags=())
    async def t_inject(s, store, m, m_case):  # type: ignore[no-untyped-def,unused-argument]  # noqa: ARG001
        assert m == "m1"
        assert s.param("m") == m
        assert m_case.id == "m1id"
        assert s.case("m") is m_case
        assert s.case("m").meta.get("k") == 1

    sd = next(s for s in iter_scenarios() if s.name == "t_inject")
    r = asyncio.run(run_scenario_job(sd, case_index=0, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail
