"""Scenario runner: queue steps and execute them with ``await materialise()``."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.match.api import check as match_check
from agent_spec_kit.match.lists import list_matcher
from agent_spec_kit.match.types import MatchResult
from agent_spec_kit.run import AdaptedAgent, TurnResult


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


@dataclass
class _ToolCallsAssertStep:
    spec: Any
    ordered: bool
    allow_extras: bool
    turn: Literal["last"]


_Step = (
    _UserMessageStep
    | _ActionStep
    | _EnvAssertStep
    | _OutputAssertStep
    | _ToolCallsAssertStep
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


def _tool_dicts_from_turn(turn: TurnResult) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for root in turn.events:
        if isinstance(root, AgentTurnEvent):
            for ch in root.children:
                if isinstance(ch, ToolCallEvent):
                    out.append(_normalize_tool_event(ch))
        elif isinstance(root, ToolCallEvent):
            out.append(_normalize_tool_event(root))
    return out


def _format_match_failure(result: MatchResult, label: str) -> str:
    parts = [f"{label} failed"]
    for err in result.errors:
        parts.append(f"  {err.path}: {err.message} (expected {err.expected!s}, got {err.actual!s})")
    return "\n".join(parts)


def _raise_if_not_ok(result: MatchResult, label: str) -> None:
    if not result.ok:
        raise AssertionError(_format_match_failure(result, label))


@dataclass
class Scenario:
    """Queued scenario steps; run with :meth:`materialise`."""

    adapted_agent: AdaptedAgent
    fixture_values: dict[str, Any] = field(default_factory=dict)
    _steps: list[_Step] = field(default_factory=list)
    _executed_until: int = 0
    _turn_results: list[TurnResult] = field(default_factory=list)

    @property
    def turn_results(self) -> tuple[TurnResult, ...]:
        return tuple(self._turn_results)

    @property
    def last_turn(self) -> TurnResult:
        if not self._turn_results:
            raise RuntimeError("no user turns yet (call user_message then materialise first)")
        return self._turn_results[-1]

    def user_message(self, text: str) -> Scenario:
        self._steps.append(_UserMessageStep(message=text))
        return self

    def action(self, fn: Callable[..., Any]) -> Scenario:
        self._steps.append(_ActionStep(fn=fn))
        return self

    def assert_that(self, fn: Callable[..., Any]) -> Scenario:
        self._steps.append(_EnvAssertStep(fn=fn))
        return self

    def assert_output(self, matcher: Any, *, turn: Literal["last"] = "last") -> Scenario:
        self._steps.append(_OutputAssertStep(matcher=matcher, turn=turn))
        return self

    def assert_tool_calls(
        self,
        spec: Any,
        *,
        ordered: bool = True,
        allow_extras: bool = True,
        turn: Literal["last"] = "last",
    ) -> Scenario:
        self._steps.append(
            _ToolCallsAssertStep(
                spec=spec,
                ordered=ordered,
                allow_extras=allow_extras,
                turn=turn,
            )
        )
        return self

    def check_output(self, spec: Any, *, turn: Literal["last"] = "last") -> MatchResult:
        self._require_post_checks_ready()
        tr = self._turn_for(turn)
        return match_check(spec, tr.output)

    def check_tool_calls(
        self,
        spec: Any,
        *,
        ordered: bool = True,
        allow_extras: bool = True,
        turn: Literal["last"] = "last",
    ) -> MatchResult:
        self._require_post_checks_ready()
        tr = self._turn_for(turn)
        actual = _tool_dicts_from_turn(tr)
        list_spec = _coerce_tool_calls_list_spec(spec, ordered=ordered, allow_extras=allow_extras)
        return match_check(list_spec, actual)

    def _require_post_checks_ready(self) -> None:
        if self._executed_until != len(self._steps):
            raise RuntimeError(
                "check_output and check_tool_calls require all queued steps to have run "
                "(await scenario.materialise() first; pending steps remain)"
            )
        if not self._turn_results:
            raise RuntimeError(
                "check_output and check_tool_calls require at least one completed user_message turn"
            )

    def _turn_for(self, turn: Literal["last"]) -> TurnResult:
        if turn != "last":
            raise ValueError(f"unsupported turn selector: {turn!r} (only 'last' is supported)")
        return self._turn_results[-1]

    async def materialise(self) -> Scenario:
        while self._executed_until < len(self._steps):
            step = self._steps[self._executed_until]
            await self._dispatch_step(step)
            self._executed_until += 1
        return self

    async def _dispatch_step(self, step: _Step) -> None:
        if isinstance(step, _UserMessageStep):
            result = await self.adapted_agent.run_turn(step.message)
            self._turn_results.append(result)
            return
        if isinstance(step, _ActionStep):
            kwargs = _resolve_fixture_kwargs(step.fn, self.fixture_values)
            await _invoke_maybe_async(step.fn, **kwargs)
            return
        if isinstance(step, _EnvAssertStep):
            await self._run_env_assert(step.fn)
            return
        if isinstance(step, _OutputAssertStep):
            tr = self._turn_for_assert_output(step.turn)
            r = match_check(step.matcher, tr.output)
            _raise_if_not_ok(r, "assert_output")
            return
        if isinstance(step, _ToolCallsAssertStep):
            tr = self._turn_for_assert_output(step.turn)
            actual = _tool_dicts_from_turn(tr)
            list_spec = _coerce_tool_calls_list_spec(
                step.spec,
                ordered=step.ordered,
                allow_extras=step.allow_extras,
            )
            r = match_check(list_spec, actual)
            _raise_if_not_ok(r, "assert_tool_calls")
            return
        raise TypeError(f"unknown step type: {type(step)!r}")

    def _turn_for_assert_output(self, turn: Literal["last"]) -> TurnResult:
        if turn != "last":
            raise ValueError(f"unsupported turn selector: {turn!r}")
        if not self._turn_results:
            raise AssertionError(
                "assert_output/assert_tool_calls require a preceding user_message step in the queue"
            )
        return self._turn_results[-1]

    async def _run_env_assert(self, fn: Callable[..., Any]) -> None:
        kwargs = _resolve_fixture_kwargs(fn, self.fixture_values)
        try:
            result = await _invoke_maybe_async(fn, **kwargs)
        except AssertionError:
            raise
        except Exception as e:
            raise AssertionError(f"assert_that callable raised: {e}") from e
        if result is False:
            raise AssertionError("assert_that callable returned False")


def _coerce_tool_calls_list_spec(
    spec: Any,
    *,
    ordered: bool,
    allow_extras: bool,
) -> Any:
    elements = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    mode: Literal["ordered", "unordered"] = "ordered" if ordered else "unordered"
    return list_matcher(elements, mode=mode, allow_extras=allow_extras)


def create_scenario(
    adapted_agent: AdaptedAgent,
    *,
    fixture_values: dict[str, Any] | None = None,
    **fixtures: Any,
) -> Scenario:
    """Build a :class:`Scenario` with optional ``fixture_values`` merged with keyword fixtures."""
    fv: dict[str, Any] = dict(fixture_values or {})
    overlap = set(fv) & set(fixtures)
    if overlap:
        raise TypeError(f"fixture keys passed both in fixture_values= and as keywords: {sorted(overlap)}")
    fv.update(fixtures)
    return Scenario(adapted_agent=adapted_agent, fixture_values=fv)


__all__ = ["Scenario", "create_scenario"]
