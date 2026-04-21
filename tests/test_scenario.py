"""Unit tests for :mod:`agent_spec_kit.scenario`."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import agent_spec_kit.match as m
from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.run import TurnResult
from agent_spec_kit.scenario import create_scenario


def _turn_with_tools(output: str, *tool_names: str) -> TurnResult:
    root = AgentTurnEvent(user_input=None, agent_output=output)
    for name in tool_names:
        root.children.append(ToolCallEvent(tool_name=name, args={"k": 1}, result="ok"))
    return TurnResult(output=output, events=(root,))


class ScriptedAgent:
    def __init__(self, responses: list[TurnResult]) -> None:
        self.responses = responses
        self._i = 0
        self.messages: list[str] = []

    async def run_turn(self, user_message: str) -> TurnResult:
        self.messages.append(user_message)
        if self._i >= len(self.responses):
            raise RuntimeError("exhausted scripted responses")
        r = self.responses[self._i]
        self._i += 1
        return r


def _run(coro):
    return asyncio.run(coro)


def test_public_package_exports_create_scenario() -> None:
    import agent_spec_kit as ek

    agent = ScriptedAgent([TurnResult(output="x", events=())])
    s = ek.create_scenario(agent)
    assert isinstance(s, ek.Scenario)


def test_create_scenario_merges_fixture_kwargs() -> None:
    agent = ScriptedAgent([TurnResult(output="hi", events=())])
    s = create_scenario(agent, repo=Path("/tmp"), db=1)
    assert s.fixture_values == {"repo": Path("/tmp"), "db": 1}
    s2 = create_scenario(agent, fixture_values={"a": 1}, b=2)
    assert s2.fixture_values == {"a": 1, "b": 2}


def test_create_scenario_rejects_duplicate_fixture_keys() -> None:
    agent = ScriptedAgent([])
    with pytest.raises(TypeError, match="both in fixture_values"):
        create_scenario(agent, fixture_values={"x": 1}, x=2)


def test_has_pending_steps() -> None:
    agent = ScriptedAgent([TurnResult(output="x", events=())])
    s = create_scenario(agent)
    assert not s.has_pending_steps
    s.user_message("a")
    assert s.has_pending_steps
    _run(s.materialise())
    assert not s.has_pending_steps


def test_raise_unless_ok_raises_scenario_assertion_failed() -> None:
    from agent_spec_kit.failures import ScenarioAssertionFailed

    agent = ScriptedAgent([TurnResult(output="x", events=())])
    s = create_scenario(agent, scenario_name="sn")
    s.user_message("hi")
    _run(s.materialise())
    r = s.check_output("nope")
    with pytest.raises(ScenarioAssertionFailed):
        s.raise_unless_ok(r, actual=s.last_turn.output, label="post_check")


def test_materialise_suffix_only() -> None:
    agent = ScriptedAgent(
        [
            TurnResult(output="first", events=()),
            TurnResult(output="second", events=()),
        ]
    )
    s = create_scenario(agent)
    s.user_message("a")
    _run(s.materialise())
    assert len(s.turn_results) == 1
    s.user_message("b")
    _run(s.materialise())
    assert len(s.turn_results) == 2
    assert agent.messages == ["a", "b"]


def test_step_order_user_message_action_assert_that(tmp_path: Path) -> None:
    log: list[str] = []

    def mark(x: str) -> None:
        log.append(x)

    agent = ScriptedAgent([TurnResult(output="done", events=())])
    s = create_scenario(agent, repo=tmp_path)

    def touch_repo(repo: Path) -> None:
        mark("action")
        (repo / "x.txt").write_text("x")

    def check_repo(repo: Path) -> None:
        mark("assert_that")
        assert (repo / "x.txt").exists()

    s.user_message("go").action(touch_repo).assert_that(check_repo).assert_output(m.contains("done"))
    _run(s.materialise())
    assert log == ["action", "assert_that"]


def test_assert_output_fails_when_no_prior_user_message() -> None:
    agent = ScriptedAgent([])
    s = create_scenario(agent)
    s.assert_output(m.contains("x"))
    with pytest.raises(AssertionError, match="preceding user_message"):
        _run(s.materialise())


def test_assert_output_and_tool_calls_match() -> None:
    agent = ScriptedAgent([_turn_with_tools("Arithmetic report", "run_specialist", "sidecar_ping")])
    s = create_scenario(agent)
    s.user_message("run").assert_output(m.contains("Arithmetic")).assert_tool_calls(
        [
            m.tool_call("run_specialist"),
            m.tool_call("sidecar_ping"),
        ],
        ordered=True,
        allow_extras=True,
    )
    _run(s.materialise())


def test_assert_tool_calls_nested_children() -> None:
    root = AgentTurnEvent(agent_output="ok")
    inner = ToolCallEvent(tool_name="inner", args={}, result="42")
    outer = ToolCallEvent(tool_name="outer", args={"t": 1}, result="x", children=[inner])
    root.children.append(outer)
    agent = ScriptedAgent([TurnResult(output="ok", events=(root,))])
    s = create_scenario(agent)
    s.user_message("x").assert_tool_calls(
        [
            m.tool_call(
                "outer",
                args={"t": 1},
                result="x",
                children=[m.tool_call("inner", args={}, result="42")],
            )
        ],
    )
    _run(s.materialise())


def test_check_output_and_check_tool_calls_after_materialise() -> None:
    agent = ScriptedAgent([_turn_with_tools("hello", "tool_a")])
    s = create_scenario(agent)
    s.user_message("hi")
    _run(s.materialise())
    out = s.check_output(m.contains("hello"))
    assert out.ok
    tools = s.check_tool_calls([m.tool_call("tool_a")])
    assert tools.ok


def test_check_output_rejects_pending_steps() -> None:
    agent = ScriptedAgent([TurnResult(output="a", events=())])
    s = create_scenario(agent)
    s.user_message("x")
    with pytest.raises(RuntimeError, match="materialise"):
        s.check_output(m.contains("a"))


def test_check_output_requires_turn() -> None:
    agent = ScriptedAgent([])
    s = create_scenario(agent)
    with pytest.raises(RuntimeError, match="at least one"):
        s.check_output(m.contains("a"))


def test_branching_with_check_tool_calls_then_second_materialise() -> None:
    agent = ScriptedAgent(
        [
            _turn_with_tools("step1", "alpha"),
            TurnResult(output="step2", events=()),
        ]
    )
    s = create_scenario(agent)
    s.user_message("first")
    _run(s.materialise())
    if s.check_tool_calls([m.tool_call("alpha")]).ok:
        s.user_message("second").assert_output(m.contains("step2"))
        _run(s.materialise())
    assert len(s.turn_results) == 2


def test_async_action_and_assert_that(tmp_path: Path) -> None:
    agent = ScriptedAgent([TurnResult(output="ok", events=())])

    async def touch(repo: Path) -> None:
        (repo / "async.txt").write_text("1")

    async def verify(repo: Path) -> None:
        assert (repo / "async.txt").read_text() == "1"

    s = create_scenario(agent, repo=tmp_path)
    s.user_message("go").action(touch).assert_that(verify)
    _run(s.materialise())


def test_assert_that_false_raises() -> None:
    agent = ScriptedAgent([TurnResult(output="x", events=())])
    s = create_scenario(agent)

    def bad() -> bool:
        return False

    s.user_message("m").assert_that(bad)
    with pytest.raises(AssertionError, match="returned False"):
        _run(s.materialise())


def test_fixture_injection_missing_key_raises() -> None:
    agent = ScriptedAgent([TurnResult(output="x", events=())])
    s = create_scenario(agent)

    def needs_repo(repo: Path) -> None:
        pass

    s.user_message("m").action(needs_repo)
    with pytest.raises(KeyError, match="fixture 'repo'"):
        _run(s.materialise())


def test_last_turn_and_turn_results() -> None:
    agent = ScriptedAgent(
        [
            TurnResult(output="a", events=()),
            TurnResult(output="b", events=()),
        ]
    )
    s = create_scenario(agent)
    s.user_message("1").user_message("2")
    _run(s.materialise())
    assert s.last_turn.output == "b"
    assert len(s.turn_results) == 2


def test_unordered_tool_calls_allow_extras_false() -> None:
    root = AgentTurnEvent(agent_output="ok")
    for name in ("b", "a"):
        root.children.append(ToolCallEvent(tool_name=name, args={}, result="r"))
    agent = ScriptedAgent([TurnResult(output="ok", events=(root,))])
    s = create_scenario(agent)
    s.user_message("x").assert_tool_calls(
        [m.tool_call("a"), m.tool_call("b")],
        ordered=False,
        allow_extras=False,
    )
    _run(s.materialise())
