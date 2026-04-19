"""
Pydantic AI: :func:`wrap_pydantic_ai_agent` consumes ``run_stream_events`` and maps
them to typed events (see :mod:`agent_spec_kit.events`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    RetryPromptPart,
    ToolReturnPart,
)
from pydantic_ai.run import AgentRunResultEvent

from agent_spec_kit.events import (
    AgentEvent,
    AgentTurnEvent,
    ToolCallEvent,
    new_event_id,
)
from agent_spec_kit.run import TurnResult

_Dynamic = Any | Callable[[str], Any]


def _resolve_dynamic(val: _Dynamic | None, user_message: str) -> Any:
    if val is None:
        return None
    if callable(val):
        return val(user_message)
    return val


def _tool_return_value(part: ToolReturnPart) -> Any:
    raw = part.content_items(mode="raw")
    if len(raw) == 1:
        return raw[0]
    return raw


def _retry_error(part: RetryPromptPart) -> str:
    if isinstance(part.content, str):
        return part.content
    return part.model_response()


class _PydanticAdaptedAgent:
    __slots__ = ("_agent", "_deps", "_turn_index", "_run_kwargs")

    def __init__(
        self,
        agent: Any,
        *,
        deps: _Dynamic | None = None,
        turn_index: int = 0,
        **run_kwargs: Any,
    ) -> None:
        self._agent = agent
        self._deps = deps
        self._turn_index = turn_index
        self._run_kwargs = run_kwargs

    async def run_turn(self, user_message: str) -> TurnResult:
        try:
            resolved = _resolve_dynamic(self._deps, user_message)
            kwargs = dict(self._run_kwargs)
            if resolved is not None:
                kwargs["deps"] = resolved

            pending: dict[str, tuple[str, Any]] = {}
            emitted: set[str] = set()
            collected: list[AgentEvent] = []
            final_output: Any = None

            async for ev in self._agent.run_stream_events(user_message, **kwargs):
                if isinstance(ev, FunctionToolCallEvent):
                    tid = ev.tool_call_id
                    pending[tid] = (ev.part.tool_name, ev.part.args)
                    continue
                if isinstance(ev, FunctionToolResultEvent):
                    tid = ev.tool_call_id
                    if tid in emitted:
                        continue
                    emitted.add(tid)
                    name, args = pending.pop(tid, ("", None))
                    res = ev.result
                    if isinstance(res, ToolReturnPart):
                        if not name:
                            name = res.tool_name
                        if res.outcome == "success":
                            collected.append(
                                ToolCallEvent(
                                    turn_index=self._turn_index,
                                    event_id=new_event_id(prefix="tool:"),
                                    parent_id=None,
                                    source_path=(),
                                    metadata={"tool_call_id": tid},
                                    tool_name=name,
                                    args=args,
                                    result=_tool_return_value(res),
                                    error=None,
                                )
                            )
                        else:
                            err = f"tool outcome={res.outcome!r}"
                            collected.append(
                                ToolCallEvent(
                                    turn_index=self._turn_index,
                                    event_id=new_event_id(prefix="tool:"),
                                    parent_id=None,
                                    source_path=(),
                                    metadata={"tool_call_id": tid},
                                    tool_name=name or res.tool_name,
                                    args=args,
                                    result=None,
                                    error=err,
                                )
                            )
                    elif isinstance(res, RetryPromptPart):
                        if not name:
                            name = res.tool_name or ""
                        collected.append(
                            ToolCallEvent(
                                turn_index=self._turn_index,
                                event_id=new_event_id(prefix="tool:"),
                                parent_id=None,
                                source_path=(),
                                metadata={"tool_call_id": tid},
                                tool_name=name,
                                args=args,
                                result=None,
                                error=_retry_error(res),
                            )
                        )
                    continue
                if isinstance(ev, AgentRunResultEvent):
                    final_output = ev.result.output

            collected.append(
                AgentTurnEvent(
                    turn_index=self._turn_index,
                    event_id=new_event_id(prefix="turn:"),
                    parent_id=None,
                    source_path=(),
                    metadata={},
                    user_input=user_message,
                    agent_output=final_output,
                    error=None,
                )
            )
            return TurnResult(
                output=final_output,
                events=tuple(collected),
                status="ok",
                error=None,
            )
        except Exception as e:
            return TurnResult(
                output=None,
                events=(),
                status="error",
                error=str(e),
            )


def wrap_pydantic_ai_agent(
    agent: Any,
    *,
    deps: _Dynamic | None = None,
    turn_index: int = 0,
    **run_kwargs: Any,
) -> _PydanticAdaptedAgent:
    """
    Wrap a Pydantic AI :class:`pydantic_ai.Agent` and drive it via
    ``run_stream_events``.

    ``deps`` may be a value or ``callable[[str], Any]`` for per-turn dependencies.
    Additional keyword arguments are forwarded to ``run_stream_events`` (for example
    ``model``, ``message_history``, ``usage_limits``, ``model_settings``).
    """
    return _PydanticAdaptedAgent(agent, deps=deps, turn_index=turn_index, **run_kwargs)


__all__ = ["wrap_pydantic_ai_agent"]
