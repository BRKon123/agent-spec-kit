"""Scenario runner: queue steps and execute them with ``await materialise()``."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent, collect_event_errors
from agent_spec_kit.failures import (
    FailureRecord,
    ScenarioAssertionFailed,
    counterexample_from_failure,
    raise_scenario_match_failure,
)
from agent_spec_kit.match.api import async_check as match_async_check
from agent_spec_kit.match.api import check as match_check
from agent_spec_kit.match.forbidden import forbidden_tool_calls_matcher
from agent_spec_kit.match.lists import list_matcher
from agent_spec_kit.match.types import MatchResult
from agent_spec_kit.fuzz_config import FuzzConfig
from agent_spec_kit.param_cases import Case
from agent_spec_kit.run import AdaptedAgent, ConversationTurn, TurnResult

@dataclass
class _UserMessageStep:
    message: str


@dataclass
class _ActionStep:
    fn: Callable[..., Any]


@dataclass
class _EnvAssertStep:
    fn: Callable[..., Any]


@dataclass
class _OutputAssertStep:
    matcher: Any
    turn: Literal["last"]
    actor: str | None


@dataclass
class _ToolCallsAssertStep:
    spec: Any
    ordered: bool
    allow_extras: bool
    turn: Literal["last"]
    actor: str | None


@dataclass
class _ForbidToolCallsStep:
    spec: Any
    ordered: bool
    turn: Literal["last"]
    actor: str | None


@dataclass
class _SimulateStep:
    max_turns: int
    stop_condition: Any | None
    seed_actor: str | None
    seed_input: str | None


@dataclass
class _FuzzConversationStep:
    fuzz_config: FuzzConfig
    trials: int
    max_user_turns: int


_Step = (
    _UserMessageStep
    | _ActionStep
    | _EnvAssertStep
    | _OutputAssertStep
    | _ToolCallsAssertStep
    | _ForbidToolCallsStep
    | _SimulateStep
    | _FuzzConversationStep
)


def _resolve_fixture_kwargs(fn: Callable[..., Any], fixture_values: dict[str, Any]) -> dict[str, Any]:
    sig = inspect.signature(fn)
    out: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise TypeError(
                f"{fn.__name__}: *args and **kwargs are not supported on scenario callables (got {param!r})"
            )
        try:
            out[name] = fixture_values[name]
        except KeyError as e:
            raise KeyError(
                f"fixture {name!r} required by {getattr(fn, '__name__', repr(fn))} "
                f"but not present in scenario fixture_values"
            ) from e
    return out


async def _invoke_maybe_async(fn: Callable[..., Any], **kwargs: Any) -> Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(**kwargs)
    result = fn(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _normalize_tool_event(ev: ToolCallEvent) -> dict[str, Any]:
    nested: list[dict[str, Any]] = []
    for ch in ev.children:
        if isinstance(ch, ToolCallEvent):
            nested.append(_normalize_tool_event(ch))
        elif isinstance(ch, AgentTurnEvent):
            for ch2 in ch.children:
                if isinstance(ch2, ToolCallEvent):
                    nested.append(_normalize_tool_event(ch2))
    return {
        "name": ev.tool_name,
        "args": ev.args,
        "result": ev.result,
        "error": ev.error,
        "children": nested,
        "metadata": dict(ev.metadata),
    }


def _tool_dicts_from_conversation_turn(turn: ConversationTurn) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for root in turn.events:
        if isinstance(root, AgentTurnEvent):
            for ch in root.children:
                if isinstance(ch, ToolCallEvent):
                    out.append(_normalize_tool_event(ch))
        elif isinstance(root, ToolCallEvent):
            out.append(_normalize_tool_event(root))
    return out


def _normalize_tool_dict(ev: dict[str, Any]) -> dict[str, Any]:
    """JSON/dict counterpart of :func:`_normalize_tool_event`."""
    nested: list[dict[str, Any]] = []
    for ch in ev.get("children") or []:
        if not isinstance(ch, dict):
            continue
        if ch.get("tool_name"):
            nested.append(_normalize_tool_dict(ch))
        elif ch.get("agent_output") is not None or ch.get("user_input") is not None:
            for ch2 in ch.get("children") or []:
                if isinstance(ch2, dict) and ch2.get("tool_name"):
                    nested.append(_normalize_tool_dict(ch2))
    return {
        "name": ev.get("tool_name", ""),
        "args": ev.get("args"),
        "result": ev.get("result"),
        "error": ev.get("error"),
        "children": nested,
        "metadata": dict(ev.get("metadata") or {}),
    }


def tool_dicts_from_turn_data(turn: ConversationTurn | dict[str, Any]) -> list[dict[str, Any]]:
    """Tool-call dicts for matcher/counterexample panels from a turn object or transcript JSON."""
    if isinstance(turn, ConversationTurn):
        return _tool_dicts_from_conversation_turn(turn)
    if not isinstance(turn, dict):
        return []
    out: list[dict[str, Any]] = []
    for root in turn.get("events") or []:
        if not isinstance(root, dict):
            continue
        if root.get("tool_name"):
            out.append(_normalize_tool_dict(root))
        elif root.get("agent_output") is not None or root.get("user_input") is not None:
            for ch in root.get("children") or []:
                if isinstance(ch, dict) and ch.get("tool_name"):
                    out.append(_normalize_tool_dict(ch))
    return out


def tool_dicts_from_transcript(
    transcript: Any, *, turn_index: int | None = None
) -> list[dict[str, Any]]:
    """Extract tool calls from a serialized transcript (last agent turn by default)."""
    if not isinstance(transcript, list) or not transcript:
        return []
    if turn_index is not None:
        if 0 <= turn_index < len(transcript):
            turn = transcript[turn_index]
            if isinstance(turn, (ConversationTurn, dict)):
                return tool_dicts_from_turn_data(turn)
        return []
    for turn in reversed(transcript):
        if isinstance(turn, ConversationTurn):
            if turn.actor == "agent":
                return tool_dicts_from_turn_data(turn)
        elif isinstance(turn, dict) and turn.get("actor") == "agent":
            return tool_dicts_from_turn_data(turn)
    return []


@dataclass
class Scenario:
    """Queued scenario steps; run with :meth:`materialise`."""

    adapted_agent: AdaptedAgent | None
    user: AdaptedAgent | None
    fixture_values: dict[str, Any] = field(default_factory=dict)
    scenario_name: str = ""
    _steps: list[_Step] = field(default_factory=list)
    _executed_until: int = 0
    _turn_results: list[ConversationTurn] = field(default_factory=list)
    # Simulation resumption
    _simulation_started: bool = False
    _next_actor: str | None = None
    _next_input: str = ""
    # Per-run parameter cases (name -> Case)
    _case_values: dict[str, Case[Any]] = field(default_factory=dict)
    #: When True, :meth:`materialise` is a no-op (used to capture queued steps without executing).
    _recording: bool = False

    @property
    def turn_results(self) -> tuple[ConversationTurn, ...]:
        return tuple(self._turn_results)

    @property
    def last_turn(self) -> ConversationTurn:
        if not self._turn_results:
            raise RuntimeError("no turns yet (add steps then materialise first)")
        return self._turn_results[-1]

    @property
    def has_pending_steps(self) -> bool:
        return self._executed_until < len(self._steps)

    def _route_user_message(self, text: str) -> str:
        """If only `user` exists, user_message drives the user; else the agent (including dual: agent)."""
        if self.adapted_agent is not None and self.user is not None:
            return "agent"
        if self.adapted_agent is not None:
            return "agent"
        if self.user is not None:
            return "user"
        msg = "user_message requires a scenario with at least one of agent or user"
        raise TypeError(msg)

    def user_message(self, text: str) -> Scenario:
        self._steps.append(_UserMessageStep(message=text))
        return self

    def simulate_conversation(
        self,
        *,
        max_turns: int,
        stop_condition: Any | None = None,
        seed_actor: str | None = None,
        seed_input: str | None = None,
    ) -> Scenario:
        """Queue a simulation segment. ``max_turns`` counts simulation messages/turns."""
        if max_turns < 1:
            raise ValueError("max_turns must be >= 1")
        self._steps.append(
            _SimulateStep(
                max_turns=max_turns,
                stop_condition=stop_condition,
                seed_actor=seed_actor,
                seed_input=seed_input,
            )
        )
        return self

    def fuzz_conversation(
        self,
        *,
        fuzz_config: FuzzConfig,
        trials: int,
        max_user_turns: int,
    ) -> Scenario:
        """Queue a fuzz segment: ``trials`` runs of up to ``max_user_turns`` generated user lines."""
        if trials < 1:
            raise ValueError("trials must be >= 1")
        if max_user_turns < 1:
            raise ValueError("max_user_turns must be >= 1")
        self._steps.append(
            _FuzzConversationStep(
                fuzz_config=fuzz_config,
                trials=trials,
                max_user_turns=max_user_turns,
            )
        )
        return self

    def action(self, fn: Callable[..., Any]) -> Scenario:
        self._steps.append(_ActionStep(fn=fn))
        return self

    def assert_that(self, fn: Callable[..., Any]) -> Scenario:
        self._steps.append(_EnvAssertStep(fn=fn))
        return self

    def assert_output(
        self, matcher: Any, *, turn: Literal["last"] = "last", actor: str | None = None
    ) -> Scenario:
        if turn != "last":
            raise ValueError("only turn='last' is supported")
        self._steps.append(_OutputAssertStep(matcher=matcher, turn=turn, actor=actor))
        return self

    def assert_tool_calls(
        self,
        spec: Any,
        *,
        ordered: bool = True,
        allow_extras: bool = True,
        turn: Literal["last"] = "last",
        actor: str | None = None,
    ) -> Scenario:
        self._steps.append(
            _ToolCallsAssertStep(
                spec=spec,
                ordered=ordered,
                allow_extras=allow_extras,
                turn=turn,
                actor=actor,
            )
        )
        return self

    def forbid_tool_calls(
        self,
        spec: Any,
        *,
        ordered: bool = True,
        allow_extras: bool = True,  # noqa: ARG002 — reserved for API symmetry
        turn: Literal["last"] = "last",
        actor: str | None = None,
    ) -> Scenario:
        del allow_extras
        self._steps.append(
            _ForbidToolCallsStep(spec=spec, ordered=ordered, turn=turn, actor=actor)
        )
        return self

    def param(self, name: str) -> Any:
        try:
            c = self._case_values[name]
        except KeyError as e:
            raise KeyError(f"unknown case parameter {name!r} (not in this scenario run)") from e
        return c.value

    def case(self, name: str) -> Case[Any]:
        try:
            return self._case_values[name]
        except KeyError as e:
            raise KeyError(f"unknown case parameter {name!r} (not in this scenario run)") from e

    def check_output(
        self, spec: Any, *, turn: Literal["last"] = "last", actor: str | None = None
    ) -> MatchResult:
        self._require_post_checks_ready()
        tr = self._conversation_for_assert(actor)
        return match_check(spec, tr.output)

    def check_tool_calls(
        self,
        spec: Any,
        *,
        ordered: bool = True,
        allow_extras: bool = True,
        turn: Literal["last"] = "last",
        actor: str | None = None,
    ) -> MatchResult:
        self._require_post_checks_ready()
        if turn != "last":
            raise ValueError("only turn='last' is supported")
        tr = self._conversation_for_assert(actor)
        actual = _tool_dicts_from_conversation_turn(tr)
        list_spec = _coerce_tool_calls_list_spec(spec, ordered=ordered, allow_extras=allow_extras)
        return match_check(list_spec, actual)

    async def async_check_output(
        self, spec: Any, *, turn: Literal["last"] = "last", actor: str | None = None
    ) -> MatchResult:
        self._require_post_checks_ready()
        if turn != "last":
            raise ValueError("only turn='last' is supported")
        tr = self._conversation_for_assert(actor)
        return await match_async_check(spec, tr.output)

    async def async_check_tool_calls(
        self,
        spec: Any,
        *,
        ordered: bool = True,
        allow_extras: bool = True,
        turn: Literal["last"] = "last",
        actor: str | None = None,
    ) -> MatchResult:
        self._require_post_checks_ready()
        if turn != "last":
            raise ValueError("only turn='last' is supported")
        tr = self._conversation_for_assert(actor)
        actual = _tool_dicts_from_conversation_turn(tr)
        list_spec = _coerce_tool_calls_list_spec(spec, ordered=ordered, allow_extras=allow_extras)
        return await match_async_check(list_spec, actual)

    def raise_unless_ok(
        self,
        result: MatchResult,
        *,
        actual: Any,
        label: str = "check",
    ) -> None:
        if result.ok:
            return
        turn_idx = len(self._turn_results) - 1 if self._turn_results else None
        raise_scenario_match_failure(
            scenario_name=self.scenario_name or "(scenario)",
            step_index=self._executed_until,
            step_kind="scenario_body",
            turn_index=turn_idx,
            result=result,
            matcher_spec=None,
            actual=actual,
            headline_prefix=label,
            events=_last_turn_events_tuple(self),
            turn_results=tuple(self._turn_results),
        )

    def _require_post_checks_ready(self) -> None:
        if self._executed_until != len(self._steps):
            raise RuntimeError(
                "check_output and check_tool_calls require all queued steps to have run "
                "(await scenario.materialise() first; pending steps remain)"
            )
        if not self._turn_results:
            raise RuntimeError(
                "check_output and check_tool_calls require at least one completed conversation turn"
            )

    def _default_assert_actor(self) -> str:
        if self._turn_results:
            return self._turn_results[-1].actor
        return "agent"

    def _conversation_for_assert(self, actor: str | None) -> ConversationTurn:
        a = self._default_assert_actor() if actor is None else actor
        for i in range(len(self._turn_results) - 1, -1, -1):
            if self._turn_results[i].actor == a:
                return self._turn_results[i]
        raise AssertionError(
            f"no turn found for assert with actor {a!r} (turn_results may be empty or missing that actor)"
        )

    async def materialise(self) -> Scenario:
        if self._recording:
            return self
        while self._executed_until < len(self._steps):
            step = self._steps[self._executed_until]
            await self._dispatch_step(step)
            self._executed_until += 1
        return self

    async def _run_agent_turn(
        self, actor: str, user_message: str
    ) -> ConversationTurn:
        if actor == "agent":
            if self.adapted_agent is None:
                msg = "simulation requires an agent (adapted_agent) for agent turns"
                raise TypeError(msg)
            tr = await self.adapted_agent.run_turn(user_message)
        elif actor == "user":
            if self.user is None:
                msg = "simulation requires a user (user) for user turns"
                raise TypeError(msg)
            tr = await self.user.run_turn(user_message)
        else:
            msg = f"actor must be 'agent' or 'user', not {actor!r}"
            raise ValueError(msg)
        return ConversationTurn.from_turn(actor, tr)

    def _other_actor(self, actor: str) -> str:
        if self.adapted_agent is not None and self.user is not None:
            return "user" if actor == "agent" else "agent"
        return actor

    def _other_actor_exists(self) -> bool:
        return self.adapted_agent is not None and self.user is not None

    def _append_turn(self, ct: ConversationTurn) -> None:
        out_v = cast(Any, ct.output)
        if not isinstance(out_v, str):
            if out_v is not None:
                out_v = str(out_v)
        self._turn_results.append(ct)
        if ct.actor == "agent":
            _raise_if_agent_turn_errors(self, ct)
        s = out_v or ""
        self._next_input = s
        self._next_actor = self._other_actor(ct.actor) if self._other_actor_exists() else ct.actor

    async def _run_simulation_segment(self, step: _SimulateStep) -> None:
        first = not self._simulation_started and not self._turn_results
        if first:
            if step.seed_actor is None or step.seed_input is None:
                msg = "the first simulate_conversation requires seed_actor= and seed_input=..."
                raise TypeError(msg)
        # Continued segments: ignore any provided seeds (resume uses _next_actor / _next_input).

        turns_in_segment = 0
        last_output_for_stop: str | None = None
        last_actor_for_stop: str | None = None

        if first:
            self._simulation_started = True
            sa = step.seed_actor
            if sa is None or step.seed_input is None:  # pragma: no cover - already checked
                raise TypeError
            if sa not in ("agent", "user"):
                raise ValueError("seed_actor must be 'agent' or 'user'")
            if sa == "agent" and self.adapted_agent is None:
                msg = "seed_actor='agent' requires adapted_agent"
                raise TypeError(msg)
            if sa == "user" and self.user is None:
                msg = "seed_actor='user' requires a user"
                raise TypeError(msg)
            tr = await self._run_agent_turn(sa, step.seed_input)
            self._append_turn(tr)
            if tr.status != "ok":
                return
            last_output_for_stop = cast(str, tr.output) if isinstance(tr.output, str) else str(tr.output)
            last_actor_for_stop = tr.actor
            turns_in_segment = 1
        else:
            if self._next_actor is None:
                msg = "no next actor to continue simulation (internal state error)"
                raise RuntimeError(msg)
            tr0 = await self._run_agent_turn(self._next_actor, self._next_input)
            self._append_turn(tr0)
            if tr0.status != "ok":
                return
            last_output_for_stop = (
                cast(str, tr0.output) if isinstance(tr0.output, str) else str(tr0.output)
            )
            last_actor_for_stop = tr0.actor
            turns_in_segment = 1

        if step.stop_condition is not None and last_output_for_stop is not None:
            r0 = await match_async_check(step.stop_condition, last_output_for_stop)
            if r0.ok and last_actor_for_stop is not None:
                return

        turn_budget = step.max_turns
        while turns_in_segment < turn_budget:
            n = self._next_actor
            if n is None:  # pragma: no cover
                break
            tnext = await self._run_agent_turn(n, self._next_input)
            self._append_turn(tnext)
            out_s = tnext.output if isinstance(tnext.output, str) else str(tnext.output) if tnext.output is not None else ""
            if step.stop_condition is not None:
                r1 = await match_async_check(step.stop_condition, out_s)
                if r1.ok:
                    return
            if tnext.status != "ok":
                return
            last_output_for_stop = out_s
            last_actor_for_stop = tnext.actor
            turns_in_segment += 1

    async def _dispatch_user_message_text(self, text: str) -> None:
        target = self._route_user_message(text)
        if target == "agent":
            if self.adapted_agent is None:
                msg = "user_message requires a scenario with an agent (adapted_agent) when not in user-only mode"
                raise TypeError(msg)
            self._turn_results.append(ConversationTurn(actor="user", output=text))
            turn_result = await self.adapted_agent.run_turn(text)
        else:
            turn_result = await self.user.run_turn(text)  # type: ignore[union-attr]
        ct = ConversationTurn.from_turn(target, turn_result)
        self._turn_results.append(ct)
        if target == "agent":
            _raise_if_agent_turn_errors(self, ct)
        out_v = ct.output if isinstance(ct.output, str) else (str(ct.output) if ct.output is not None else "")
        self._next_input = out_v
        self._next_actor = self._other_actor(ct.actor) if self._other_actor_exists() else ct.actor
        self._simulation_started = True

    async def _dispatch_step(self, step: _Step) -> None:
        if isinstance(step, _UserMessageStep):
            await self._dispatch_user_message_text(step.message)
            return
        if isinstance(step, _ActionStep):
            kwargs = _resolve_fixture_kwargs(step.fn, self.fixture_values)
            await _invoke_maybe_async(step.fn, **kwargs)
            return
        if isinstance(step, _SimulateStep):
            await self._run_simulation_segment(step)
            return
        if isinstance(step, _FuzzConversationStep):
            raise RuntimeError(
                "fuzz_conversation must run via the generative orchestrator; was the runner bypassed?"
            )
        if isinstance(step, _EnvAssertStep):
            await self._run_env_assert(step.fn)
            return
        if isinstance(step, _OutputAssertStep):
            if not self._turn_results:
                msg = "assert_output/assert_tool_calls require a preceding user_message step in the queue"
                raise AssertionError(msg)
            conversation_turn = self._conversation_for_assert(step.actor)
            r = await match_async_check(step.matcher, conversation_turn.output)
            _raise_match_step(
                self,
                step_kind="assert_output",
                label="assert_output",
                result=r,
                matcher_spec=step.matcher,
                actual=conversation_turn.output,
            )
            return
        if isinstance(step, _ToolCallsAssertStep):
            if not self._turn_results:
                msg = "assert_output/assert_tool_calls require a preceding user_message step in the queue"
                raise AssertionError(msg)
            if step.turn != "last":
                raise ValueError("only turn='last' is supported")
            conversation_turn = self._conversation_for_assert(step.actor)
            actual = _tool_dicts_from_conversation_turn(conversation_turn)
            list_spec = _coerce_tool_calls_list_spec(
                step.spec,
                ordered=step.ordered,
                allow_extras=step.allow_extras,
            )
            r = await match_async_check(list_spec, actual)
            _raise_match_step(
                self,
                step_kind="assert_tool_calls",
                label="assert_tool_calls",
                result=r,
                matcher_spec=step.spec,
                actual=actual,
            )
            return
        if isinstance(step, _ForbidToolCallsStep):
            if not self._turn_results:
                msg = "forbid_tool_calls require a preceding user_message step in the queue"
                raise AssertionError(msg)
            if step.turn != "last":
                raise ValueError("only turn='last' is supported")
            conversation_turn = self._conversation_for_assert(step.actor)
            actual = _tool_dicts_from_conversation_turn(conversation_turn)
            forbid_spec = forbidden_tool_calls_matcher(step.spec, ordered=step.ordered)
            r = await match_async_check(forbid_spec, actual)
            _raise_match_step(
                self,
                step_kind="forbid_tool_calls",
                label="forbid_tool_calls",
                result=r,
                matcher_spec=step.spec,
                actual=actual,
            )
            return
        raise TypeError(f"unknown step type: {type(step)!r}")

    async def _run_env_assert(self, fn: Callable[..., Any]) -> None:
        kwargs = _resolve_fixture_kwargs(fn, self.fixture_values)
        try:
            result = await _invoke_maybe_async(fn, **kwargs)
        except ScenarioAssertionFailed:
            raise
        except AssertionError as e:
            turn_idx = len(self._turn_results) - 1 if self._turn_results else None
            record = FailureRecord(
                scenario_name=self.scenario_name or "(scenario)",
                step_index=self._executed_until,
                step_kind="assert_that",
                turn_index=turn_idx,
                actual=(),
                matcher_spec=None,
                matcher_errors=(),
                error=e,
                events=_last_turn_events_tuple(self),
                turn_results=tuple(self._turn_results),
                assertion_index_after_turn=_assertion_index_after_turn(self, step_kind="assert_that"),
            )
            raise ScenarioAssertionFailed(counterexample_from_failure(record), record=record) from e
        except Exception as e:
            turn_idx = len(self._turn_results) - 1 if self._turn_results else None
            record = FailureRecord(
                scenario_name=self.scenario_name or "(scenario)",
                step_index=self._executed_until,
                step_kind="assert_that",
                turn_index=turn_idx,
                actual=(),
                matcher_spec=None,
                matcher_errors=(),
                error=AssertionError(f"assert_that callable raised: {e}"),
                events=_last_turn_events_tuple(self),
                turn_results=tuple(self._turn_results),
                assertion_index_after_turn=_assertion_index_after_turn(self, step_kind="assert_that"),
            )
            raise ScenarioAssertionFailed(counterexample_from_failure(record), record=record) from e
        if result is False:
            turn_idx = len(self._turn_results) - 1 if self._turn_results else None
            record = FailureRecord(
                scenario_name=self.scenario_name or "(scenario)",
                step_index=self._executed_until,
                step_kind="assert_that",
                turn_index=turn_idx,
                actual=False,
                matcher_spec=None,
                matcher_errors=(),
                error=AssertionError("assert_that callable returned False"),
                events=_last_turn_events_tuple(self),
                turn_results=tuple(self._turn_results),
                assertion_index_after_turn=_assertion_index_after_turn(self, step_kind="assert_that"),
            )
            raise ScenarioAssertionFailed(counterexample_from_failure(record), record=record) from None


def _agent_turn_error_messages(ct: ConversationTurn) -> tuple[str, ...]:
    if ct.actor != "agent":
        return ()
    msgs: list[str] = []
    if ct.error:
        msgs.append(ct.error)
    if ct.status == "error" and ct.error is None:
        msgs.append("agent turn failed")
    for root in ct.events:
        for err in collect_event_errors(root):
            if err not in msgs:
                msgs.append(err)
    return tuple(msgs)


def _raise_if_agent_turn_errors(scenario: Scenario, ct: ConversationTurn) -> None:
    errs = _agent_turn_error_messages(ct)
    if not errs:
        return
    headline = errs[0]
    if len(errs) > 1:
        headline = f"{headline} (+{len(errs) - 1} more agent error(s))"
    turn_idx = len(scenario._turn_results) - 1
    record = FailureRecord(
        scenario_name=scenario.scenario_name or "(scenario)",
        step_index=scenario._executed_until,
        step_kind="agent_error",
        turn_index=turn_idx,
        actual=errs,
        matcher_spec=None,
        matcher_errors=(),
        error=AssertionError(headline),
        events=_last_turn_events_tuple(scenario),
        turn_results=tuple(scenario._turn_results),
    )
    raise ScenarioAssertionFailed(counterexample_from_failure(record), record=record) from None


def _last_turn_events_tuple(scenario: Scenario) -> tuple[Any, ...] | None:
    if not scenario._turn_results:
        return None
    ev = scenario._turn_results[-1].events
    if not ev:
        return None
    return tuple(ev)


def _assertion_index_after_turn(scenario: Scenario, *, step_kind: str) -> int | None:
    step_types = {
        "assert_output": _OutputAssertStep,
        "assert_tool_calls": _ToolCallsAssertStep,
        "forbid_tool_calls": _ForbidToolCallsStep,
        "assert_that": _EnvAssertStep,
    }
    step_type = step_types.get(step_kind)
    if step_type is None:
        return None
    if scenario._executed_until < 0 or scenario._executed_until >= len(scenario._steps):
        return None
    start = 0
    for i in range(scenario._executed_until, -1, -1):
        if isinstance(scenario._steps[i], (_UserMessageStep, _SimulateStep, _FuzzConversationStep)):
            start = i + 1
            break
    count = 0
    for i in range(start, scenario._executed_until + 1):
        if isinstance(scenario._steps[i], step_type):
            count += 1
    return count if count > 0 else None


def _raise_match_step(
    scenario: Scenario,
    *,
    step_kind: str,
    label: str,
    result: MatchResult,
    matcher_spec: Any,
    actual: Any,
) -> None:
    if result.ok:
        return
    turn_idx = len(scenario._turn_results) - 1 if scenario._turn_results else None
    raise_scenario_match_failure(
        scenario_name=scenario.scenario_name or "(scenario)",
        step_index=scenario._executed_until,
        step_kind=step_kind,
        turn_index=turn_idx,
        result=result,
        matcher_spec=matcher_spec,
        actual=actual,
        headline_prefix=label,
        events=_last_turn_events_tuple(scenario),
        turn_results=tuple(scenario._turn_results),
        assertion_index_after_turn=_assertion_index_after_turn(scenario, step_kind=step_kind),
    )


def _coerce_tool_calls_list_spec(
    spec: Any,
    *,
    ordered: bool,
    allow_extras: bool,
) -> Any:
    elements = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    mode: Literal["ordered", "unordered"] = "ordered" if ordered else "unordered"
    return list_matcher(elements, mode=mode, allow_extras=allow_extras)


def scenario_fuzz_metadata(s: Scenario) -> dict[str, Any] | None:
    """Return JSON-serialisable fuzz step metadata if the scenario queues ``fuzz_conversation``."""
    fuzz_steps = [st for st in s._steps if isinstance(st, _FuzzConversationStep)]
    if not fuzz_steps:
        return None
    st0 = fuzz_steps[0]
    meta: dict[str, Any] = {
        "strategy_kind": type(st0.fuzz_config.strategy).__name__,
        "seed": st0.fuzz_config.seed,
        "seed_inputs": list(st0.fuzz_config.seed_inputs),
        "trials": st0.trials,
        "max_user_turns": st0.max_user_turns,
    }
    if len(fuzz_steps) > 1:
        meta["fuzz_step_count"] = len(fuzz_steps)
        meta["trials_by_step"] = [x.trials for x in fuzz_steps]
    return meta


def create_scenario(
    *args: Any,
    user: AdaptedAgent | None = None,
    case_values: dict[str, Case[Any]] | None = None,
    fixture_values: dict[str, Any] | None = None,
    scenario_name: str = "",
    recording: bool = False,
    **fixtures: Any,
) -> Scenario:
    """Build a :class:`Scenario`.

    Pass the agent as the first positional argument, or use ``user=`` only for user-only runs.
    """
    if len(args) > 1:
        msg = "create_scenario accepts at most one positional argument (the adapted agent)"
        raise TypeError(msg)
    adapted_agent: AdaptedAgent | None = args[0] if args else None
    if adapted_agent is None and user is None:
        msg = "create_scenario requires at least one of: agent (positional) or user="
        raise TypeError(msg)
    fv: dict[str, Any] = dict(fixture_values or {})
    overlap = set(fv) & set(fixtures)
    if overlap:
        raise TypeError(
            f"fixture keys passed both in fixture_values= and as keywords: {sorted(overlap)}"
        )
    fv.update(fixtures)
    cv: dict[str, Case[Any]] = dict(case_values or {})
    return Scenario(
        adapted_agent=adapted_agent,
        user=user,
        fixture_values=fv,
        scenario_name=scenario_name,
        _case_values=cv,
        _recording=recording,
    )


__all__ = ["Scenario", "create_scenario", "scenario_fuzz_metadata"]
