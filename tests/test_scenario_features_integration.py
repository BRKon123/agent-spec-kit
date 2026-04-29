"""Broader integration tests for simulation, parametrise, and runner injection."""

from __future__ import annotations

import asyncio

import pytest

import agent_spec_kit as ek
import agent_spec_kit.match as m
from agent_spec_kit import create_scenario
from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.param_cases import normalize_case
from agent_spec_kit.registries import iter_scenarios, reset_registries
from agent_spec_kit.run import TurnResult
from agent_spec_kit.runner import JobResult, run_scenario_job


def _run(c):
    return asyncio.run(c)


class _Scripted:
    def __init__(self, outputs: list[TurnResult]) -> None:
        self._i = 0
        self.outputs = outputs
        self.received: list[str] = []

    async def run_turn(self, user_message: str) -> TurnResult:
        self.received.append(user_message)
        if self._i >= len(self.outputs):
            return TurnResult(
                output="(exhausted)", events=(), status="error", error="exhausted"
            )
        r = self.outputs[self._i]
        self._i += 1
        return r


def _tr(out: str, *tool_names: str) -> TurnResult:
    root = AgentTurnEvent(user_input=None, agent_output=out)
    for name in tool_names:
        root.children.append(ToolCallEvent(tool_name=name, args={"k": 1}, result="ok"))
    return TurnResult(output=out, events=(root,))


def test_stop_condition_exits_before_max_turns() -> None:
    u = _Scripted([TurnResult(output="user line", events=())])
    a = _Scripted([TurnResult(output="###STOP###", events=())])
    s = create_scenario(a, user=u)
    s.simulate_conversation(
        seed_actor="user",
        seed_input="z",
        max_turns=10,
        stop_condition=m.contains("###STOP###"),
    )
    _run(s.materialise())
    assert u._i == 1 and a._i == 1
    assert a.received[0] == "user line"
    assert s.turn_results[1].output == "###STOP###"


def test_agent_only_seeded_simulation_continues_on_one_side() -> None:
    outputs = [TurnResult(output="one", events=()), TurnResult(output="two", events=())]
    a = _Scripted(outputs)
    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="ticket-1", max_turns=2)
    _run(s.materialise())
    assert a.received == ["ticket-1", "one"]
    assert len(s.turn_results) == 2
    assert s.turn_results[0].actor == s.turn_results[1].actor == "agent"


def test_user_only_routes_user_message_to_user() -> None:
    u = _Scripted([TurnResult(output="from user model", events=())])
    s = create_scenario(user=u)
    s.user_message("hi")
    _run(s.materialise())
    assert u.received == ["hi"]
    assert s.last_turn.actor == "user"
    assert s.last_turn.output == "from user model"


def test_user_only_simulation_seeds_user() -> None:
    u = _Scripted(
        [TurnResult(output="first u", events=()), TurnResult(output="second u", events=())]
    )
    s = create_scenario(user=u)
    s.simulate_conversation(seed_actor="user", seed_input="seeded", max_turns=2)
    _run(s.materialise())
    assert u.received[0] == "seeded"
    assert u.received[1] == "first u"
    assert len(s.turn_results) == 2


def test_simulation_stops_when_turn_status_not_ok() -> None:
    bad = TurnResult(output="e", events=(), status="error", error="boom")
    a = _Scripted([bad, TurnResult(output="never", events=())])
    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="s", max_turns=3)
    _run(s.materialise())
    assert len(s.turn_results) == 1
    assert s.turn_results[0].status == "error"


def test_three_simulation_steps_two_continuations() -> None:
    a = _Scripted(
        [TurnResult(output="t1", events=()), TurnResult(output="t2", events=()), TurnResult(output="t3", events=())]
    )
    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="a0", max_turns=1)
    s.simulate_conversation(max_turns=1)
    s.simulate_conversation(max_turns=1)
    _run(s.materialise())
    assert len(s.turn_results) == 3
    assert a.received == ["a0", "t1", "t2"]


def test_action_mutates_state_between_simulation_segments() -> None:
    a = _Scripted(
        [TurnResult(output="x1", events=()), TurnResult(output="x2", events=())]
    )
    seen: list[int] = []

    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="0", max_turns=1)

    def mark() -> None:
        seen.append(1)

    s.action(mark).simulate_conversation(max_turns=1)
    _run(s.materialise())
    assert seen == [1]
    assert len(s.turn_results) == 2


def test_assert_tool_calls_targets_agent_explicitly_in_simulation() -> None:
    a = _Scripted(
        [
            _tr("with tools", "use_tool_a"),
            TurnResult(output="plain", events=()),
        ]
    )
    u = _Scripted([TurnResult(output="u speaks", events=())])
    s = create_scenario(a, user=u)
    s.simulate_conversation(seed_actor="user", seed_input="h", max_turns=2)
    s.assert_tool_calls([m.tool_call("use_tool_a")], actor="agent", ordered=True, allow_extras=True)
    _run(s.materialise())


# --- @ek registry integration ---


def test_inconsistent_parametrize_same_axis_different_ids_raises() -> None:
    reset_registries()

    @ek.fixture
    @ek.parametrize("x", [ek.case(1, id="one")])
    def left(x):  # type: ignore[no-untyped-def]
        return x

    @ek.fixture
    @ek.parametrize("x", [ek.case(2, id="two")])
    def right(x):  # type: ignore[no-untyped-def]
        return x

    @ek.fixture
    def agent(left, right):  # type: ignore[no-untyped-def]  # noqa: ARG001
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="o", events=())

        return A()

    @ek.scenario(agent_fixture="agent", tags=())
    async def t_conflict(s):  # type: ignore[no-untyped-def,unused-argument]  # noqa: ARG001
        pass

    sd = next(s for s in iter_scenarios() if s.name == "t_conflict")
    with pytest.raises(ValueError, match="inconsistent @parametrize"):
        scenario_case_runs(sd)


def test_scenario_unknown_parameter_in_signature_fails_at_run() -> None:
    reset_registries()

    @ek.fixture
    def agent():  # type: ignore[no-untyped-def]
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="k", events=())

        return A()

    @ek.scenario(agent_fixture="agent", tags=())
    async def t_no_such(s, not_in_graph):  # type: ignore[no-untyped-def,unused-argument]  # noqa: ARG001
        pass

    sd = next(s for s in iter_scenarios() if s.name == "t_no_such")
    r = asyncio.run(run_scenario_job(sd, case_index=0, repeat_index=1, repeat_total=1))
    assert not r.ok
    assert r.detail is not None
    assert "not_in_graph" in r.detail or "unknown scenario parameter" in r.detail


def test_normalize_id_only_object() -> None:
    class P:
        id = "p0"

    c = normalize_case(P())
    assert c.id == "p0"
    assert c.name is None
    assert c.meta == {}


def test_jobresult_display_name_includes_case_id() -> None:
    r = JobResult(
        ok=True,
        scenario_name="foo",
        case_id="a=1+b=2",
        duration_s=0.01,
    )
    assert r.display_name == "foo [a=1+b=2]"


def test_user_fixture_scenario_runs() -> None:
    reset_registries()

    @ek.fixture
    def u():  # type: ignore[no-untyped-def]
        class U:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="u-out", events=())

        return U()

    @ek.scenario(user_fixture="u", tags=())
    async def t_user_only(s):  # type: ignore[no-untyped-def,unused-argument]  # noqa: ARG001
        s.user_message("ping")

    sd = next(s for s in iter_scenarios() if s.name == "t_user_only")
    r = asyncio.run(run_scenario_job(sd, case_index=0, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail
    assert "default" in (r.case_id,)


def test_check_output_and_tool_calls_post_simulation() -> None:
    a = _Scripted(
        [
            _tr("with tool", "t1"),
        ]
    )
    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="s", max_turns=1)
    _run(s.materialise())
    assert s.check_output(m.contains("with tool")).ok
    assert s.check_tool_calls([m.tool_call("t1")], ordered=True, allow_extras=True).ok


def test_cartesian_injects_both_axes_and_case_objects() -> None:
    reset_registries()

    @ek.fixture
    @ek.parametrize("a", [ek.case(1, id="a1", meta={"n": 1})])
    @ek.parametrize("b", [ek.case(2, id="b1")])
    def base(a, b):  # type: ignore[no-untyped-def]
        return 0

    @ek.fixture
    def agent(base):  # type: ignore[no-untyped-def,unused-argument]  # noqa: ARG001
        class A:
            async def run_turn(self, user_message: str) -> TurnResult:
                return TurnResult(output="k", events=())

        return A()

    @ek.scenario(agent_fixture="agent", tags=())
    async def t_cart(s, a, b, a_case, b_case):  # type: ignore[no-untyped-def,unused-argument]  # noqa: ARG001
        assert a == 1 and b == 2
        assert a_case.id == "a1" and a_case.meta.get("n") == 1
        assert b_case.id == "b1"

    sd = next(s for s in iter_scenarios() if s.name == "t_cart")
    r = asyncio.run(run_scenario_job(sd, case_index=0, repeat_index=1, repeat_total=1))
    assert r.ok, r.detail
    assert r.case_id == "a=a1+b=b1"


def test_dual_max_turns_is_per_message() -> None:
    """In dual control, max_turns counts simulation messages/turns."""
    a = _Scripted(
        [TurnResult(output="a1", events=()), TurnResult(output="a2", events=())]
    )
    u = _Scripted(
        [TurnResult(output="u1", events=()), TurnResult(output="u2", events=())]
    )
    s = create_scenario(a, user=u)
    s.simulate_conversation(seed_actor="user", seed_input="s0", max_turns=2)
    _run(s.materialise())
    assert len(s.turn_results) == 2


def test_solo_max_turns_is_per_message() -> None:
    a = _Scripted(
        [
            TurnResult(output="1", events=()),
            TurnResult(output="2", events=()),
            TurnResult(output="3", events=()),
        ]
    )
    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="0", max_turns=2)
    _run(s.materialise())
    assert len(s.turn_results) == 2


def test_conversation_turn_exposes_error_fields() -> None:
    a = _Scripted([TurnResult(output="e", events=(), status="error", error="x")])
    s = create_scenario(a)
    s.simulate_conversation(seed_actor="agent", seed_input="s", max_turns=2)
    _run(s.materialise())
    t0 = s.turn_results[0]
    assert t0.status == "error" and t0.error == "x"

