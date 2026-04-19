"""
A lil janky, and uses internal pydantic_ai API which perhap we should not touch.
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

from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent, new_event_id
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


def _wrapped_agent_function_tool_names(agent: Any) -> frozenset[str]:
    """Names of function tools registered on this agent (not nested inner agents)."""
    toolset = getattr(agent, "_function_toolset", None)
    if toolset is None:
        return frozenset()
    tools = getattr(toolset, "tools", None)
    if not isinstance(tools, dict):
        return frozenset()
    return frozenset(tools.keys())


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

            emitted: set[str] = set()
            final_output: Any = None
            open_stack: list[tuple[str, ToolCallEvent]] = []
            tid_to_node: dict[str, ToolCallEvent] = {}
            outer_tool_names = _wrapped_agent_function_tool_names(self._agent)

            root = AgentTurnEvent(
                turn_index=self._turn_index,
                event_id=new_event_id(prefix="turn:"),
                source_path=(),
                metadata={},
                user_input=user_message,
                agent_output=None,
                error=None,
            )

            def attachment_parent() -> AgentTurnEvent | ToolCallEvent:
                if not open_stack:
                    return root
                return open_stack[-1][1]

            def attachment_for_tool_call(tool_name: str) -> AgentTurnEvent | ToolCallEvent:
                # Outer-agent tools always hang off the root turn so parallel calls stay siblings.
                # Nested inner-agent tools are not in this set and attach under the in-flight tool.
                if tool_name in outer_tool_names:
                    return root
                return attachment_parent()

            async for ev in self._agent.run_stream_events(user_message, **kwargs):
                if isinstance(ev, FunctionToolCallEvent):
                    tid = ev.tool_call_id
                    parent = attachment_for_tool_call(ev.part.tool_name)
                    node = ToolCallEvent(
                        turn_index=self._turn_index,
                        event_id=new_event_id(prefix="tool:"),
                        source_path=(),
                        metadata={"tool_call_id": tid},
                        tool_name=ev.part.tool_name,
                        args=ev.part.args,
                        result=None,
                        error=None,
                    )
                    parent.children.append(node)
                    open_stack.append((tid, node))
                    tid_to_node[tid] = node
                    continue
                if isinstance(ev, FunctionToolResultEvent):
                    tid = ev.tool_call_id
                    if tid in emitted:
                        continue
                    emitted.add(tid)
                    node = tid_to_node.pop(tid) if tid in tid_to_node else None
                    open_stack = [(t, n) for t, n in open_stack if t != tid]
                    res = ev.result
                    if node is None:
                        res_name = (
                            res.tool_name
                            if isinstance(res, (ToolReturnPart, RetryPromptPart))
                            else ""
                        )
                        parent = (
                            attachment_for_tool_call(res_name)
                            if res_name
                            else attachment_parent()
                        )
                        if isinstance(res, ToolReturnPart):
                            name = res.tool_name
                            if res.outcome == "success":
                                node = ToolCallEvent(
                                    turn_index=self._turn_index,
                                    event_id=new_event_id(prefix="tool:"),
                                    source_path=(),
                                    metadata={"tool_call_id": tid},
                                    tool_name=name,
                                    args=None,
                                    result=_tool_return_value(res),
                                    error=None,
                                )
                            else:
                                err = f"tool outcome={res.outcome!r}"
                                node = ToolCallEvent(
                                    turn_index=self._turn_index,
                                    event_id=new_event_id(prefix="tool:"),
                                    source_path=(),
                                    metadata={"tool_call_id": tid},
                                    tool_name=name,
                                    args=None,
                                    result=None,
                                    error=err,
                                )
                        elif isinstance(res, RetryPromptPart):
                            name = res.tool_name or ""
                            node = ToolCallEvent(
                                turn_index=self._turn_index,
                                event_id=new_event_id(prefix="tool:"),
                                source_path=(),
                                metadata={"tool_call_id": tid},
                                tool_name=name,
                                args=None,
                                result=None,
                                error=_retry_error(res),
                            )
                        else:
                            continue
                        parent.children.append(node)
                        continue

                    if isinstance(res, ToolReturnPart):
                        if not node.tool_name:
                            node.tool_name = res.tool_name
                        if res.outcome == "success":
                            node.result = _tool_return_value(res)
                            node.error = None
                        else:
                            node.result = None
                            node.error = f"tool outcome={res.outcome!r}"
                    elif isinstance(res, RetryPromptPart):
                        if not node.tool_name:
                            node.tool_name = res.tool_name or ""
                        node.result = None
                        node.error = _retry_error(res)
                    continue
                if isinstance(ev, AgentRunResultEvent):
                    final_output = ev.result.output

            root.agent_output = final_output
            return TurnResult(
                output=final_output,
                events=(root,),
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

    Tool calls whose names are registered on this agent attach under the root
    ``AgentTurnEvent`` so parallel outer tools stay siblings. Calls from nested
    inner agents (names not in that set) nest under the currently in-flight tool.

    ``deps`` may be a value or ``callable[[str], Any]`` for per-turn dependencies.
    Additional keyword arguments are forwarded to ``run_stream_events`` (for example
    ``model``, ``message_history``, ``usage_limits``, ``model_settings``).
    """
    return _PydanticAdaptedAgent(agent, deps=deps, turn_index=turn_index, **run_kwargs)


__all__ = ["wrap_pydantic_ai_agent"]
