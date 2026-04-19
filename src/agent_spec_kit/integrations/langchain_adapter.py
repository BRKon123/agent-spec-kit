"""
LangChain / LangGraph: :func:`wrap_langchain_agent` streams ``astream`` updates
and maps them to typed events (see :mod:`agent_spec_kit.events`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agent_spec_kit.events import (
    AgentEvent,
    AgentTurnEvent,
    SubagentCallEvent,
    ToolCallEvent,
    new_event_id,
)
from agent_spec_kit.run import TurnResult

_Dynamic = Any | Callable[[str], Any]

# internal stream normalisation

def unpack_stream_chunk(chunk: Any) -> tuple[tuple[str, ...], dict[str, Any]]:
    """
    Normalize LangGraph ``.stream()`` / ``.astream()`` chunks to
    ``(source_path, updates_dict)``.
    """
    if isinstance(chunk, tuple):
        if len(chunk) == 3:
            ns, _mode, payload = chunk
            if isinstance(ns, tuple) and isinstance(payload, dict):
                return tuple(str(x) for x in ns), payload
        if len(chunk) == 2:
            a, b = chunk
            if isinstance(a, tuple) and isinstance(b, dict):
                return tuple(str(x) for x in a), b
            if isinstance(a, tuple) and isinstance(b, (list, tuple)):
                return tuple(str(x) for x in a), {}
    if isinstance(chunk, dict):
        return (), chunk
    return (), {}


def _message_text(msg: BaseMessage) -> Any:
    c = msg.content
    if isinstance(c, str):
        return c
    return c


def _register_ai_tool_calls(state: _ToolCallArgs, ai: AIMessage) -> None:
    for tc in ai.tool_calls or []:
        if not isinstance(tc, dict):
            continue
        tid = tc.get("id")
        if tid is None:
            continue
        state.known[tid] = (tc.get("name") or "", tc.get("args"))


class _ToolCallArgs:
    __slots__ = ("known",)

    def __init__(self) -> None:
        self.known: dict[str, tuple[str, Any]] = {}


class UpdatesNormalizer:
    """State machine over LangGraph ``updates`` stream chunks."""

    __slots__ = (
        "_first_human",
        "_tool_args",
        "_emitted_tools",
        "_last_ai_by_ns",
        "_pending_root_error",
        "_pending_sub_errors",
        "_turn_index",
    )

    def __init__(self, turn_index: int = 0) -> None:
        self._turn_index = turn_index
        self._first_human: Any = None
        self._tool_args = _ToolCallArgs()
        self._emitted_tools: set[str] = set()
        self._last_ai_by_ns: dict[tuple[str, ...], AIMessage] = {}
        self._pending_root_error: str | None = None
        self._pending_sub_errors: dict[tuple[str, ...], str] = {}

    def feed(
        self,
        source_path: tuple[str, ...],
        updates: Mapping[str, Any],
    ) -> list[AgentEvent]:
        out: list[AgentEvent] = []
        for _node_name, partial in updates.items():
            if not isinstance(partial, dict):
                continue
            messages = partial.get("messages")
            if not isinstance(messages, list):
                continue
            for msg in messages:
                if not isinstance(msg, BaseMessage):
                    continue
                out.extend(self._feed_message(source_path, msg))
        return out

    def _feed_message(
        self,
        source_path: tuple[str, ...],
        msg: BaseMessage,
    ) -> list[AgentEvent]:
        out: list[AgentEvent] = []
        if isinstance(msg, HumanMessage) and self._first_human is None:
            self._first_human = _message_text(msg)

        if isinstance(msg, AIMessage):
            if getattr(msg, "tool_calls", None):
                _register_ai_tool_calls(self._tool_args, msg)
            else:
                self._last_ai_by_ns[source_path] = msg
                err = _error_from_message(msg)
                if source_path:
                    if err:
                        self._pending_sub_errors[source_path] = err
                else:
                    if err:
                        self._pending_root_error = err
            return out

        if isinstance(msg, ToolMessage):
            tid = msg.tool_call_id or ""
            if tid and tid in self._emitted_tools:
                return out
            name, args = self._tool_args.known.get(tid, ("", None))
            if not name:
                name = msg.name or ""
            err = _error_from_message(msg)
            meta: dict[str, Any] = {}
            if tid:
                meta["tool_call_id"] = tid
            ev = ToolCallEvent(
                turn_index=self._turn_index,
                event_id=new_event_id(prefix="tool:"),
                parent_id=None,
                source_path=source_path,
                metadata=meta,
                tool_name=name,
                args=args,
                result=None if err else msg.content,
                error=err,
            )
            out.append(ev)
            if tid:
                self._emitted_tools.add(tid)
            return out

        return out

    def finalize(self) -> list[AgentEvent]:
        out: list[AgentEvent] = []
        root_ai = self._last_ai_by_ns.get(())
        if root_ai is not None:
            err = self._pending_root_error
            out.append(
                AgentTurnEvent(
                    turn_index=self._turn_index,
                    event_id=new_event_id(prefix="turn:"),
                    parent_id=None,
                    source_path=(),
                    metadata={},
                    user_input=self._first_human,
                    agent_output=_message_text(root_ai),
                    error=err,
                )
            )
        for ns, ai in self._last_ai_by_ns.items():
            if not ns:
                continue
            name = ns[-1] if ns else "subagent"
            err = self._pending_sub_errors.get(ns)
            out.append(
                SubagentCallEvent(
                    turn_index=self._turn_index,
                    event_id=new_event_id(prefix="sub:"),
                    parent_id=None,
                    source_path=ns,
                    metadata={},
                    agent_name=name,
                    call_input=None,
                    call_output=_message_text(ai),
                    error=err,
                )
            )
        return out


def _error_from_message(msg: BaseMessage) -> str | None:
    o = getattr(msg, "additional_kwargs", None)
    if isinstance(o, dict) and "error" in o:
        e = o["error"]
        if isinstance(e, str):
            return e
    status = getattr(msg, "status", None)
    if status == "error":
        c = msg.content
        if isinstance(c, str):
            return c
    return None



def _coerce_stream_chunk(chunk: Any) -> Any:
    if isinstance(chunk, dict):
        if chunk.get("type") == "updates" and isinstance(chunk.get("data"), dict):
            return chunk["data"]
        inner = chunk.get("updates")
        if isinstance(inner, dict):
            return inner
    return chunk


def _resolve_dynamic(val: _Dynamic | None, user_message: str) -> Any:
    if val is None:
        return None
    if callable(val):
        return val(user_message)
    return val


def root_turn_output(events: Sequence[AgentEvent]) -> Any:
    """Last root-level ``AgentTurnEvent.agent_output``, if any."""
    for ev in reversed(events):
        if isinstance(ev, AgentTurnEvent) and ev.source_path == ():
            return ev.agent_output
    return None


class _LangChainAdaptedAgent:
    __slots__ = (
        "_graph",
        "_initial_input_factory",
        "_stream_mode",
        "_version",
        "_subgraphs",
        "_context",
        "_config",
        "_turn_index",
    )

    def __init__(
        self,
        graph: Any,
        initial_input_factory: Callable[[str], dict[str, Any]],
        *,
        stream_mode: str | list[str] = "updates",
        version: str = "v2",
        subgraphs: bool = False,
        context: _Dynamic | None = None,
        config: _Dynamic | None = None,
        turn_index: int = 0,
    ) -> None:
        self._graph = graph
        self._initial_input_factory = initial_input_factory
        self._stream_mode = stream_mode
        self._version = version
        self._subgraphs = subgraphs
        self._context = context
        self._config = config
        self._turn_index = turn_index

    async def run_turn(self, user_message: str) -> TurnResult:
        try:
            inp = self._initial_input_factory(user_message)
            cfg = _resolve_dynamic(self._config, user_message)
            ctx = _resolve_dynamic(self._context, user_message)
            norm = UpdatesNormalizer(turn_index=self._turn_index)
            collected: list[AgentEvent] = []
            kwargs: dict[str, Any] = {
                "stream_mode": self._stream_mode,
                "subgraphs": self._subgraphs,
                "version": self._version,
            }
            if ctx is not None:
                kwargs["context"] = ctx
            async for raw in self._graph.astream(inp, config=cfg, **kwargs):
                chunk = _coerce_stream_chunk(raw)
                ns, updates = unpack_stream_chunk(chunk)
                for node_name, partial in updates.items():
                    collected.extend(norm.feed(ns, {node_name: partial}))
            collected.extend(norm.finalize())
            out = root_turn_output(collected)
            return TurnResult(
                output=out,
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


def wrap_langchain_agent(
    graph: Any,
    initial_input_factory: Callable[[str], dict[str, Any]],
    *,
    stream_mode: str | list[str] = "updates",
    version: str = "v2",
    subgraphs: bool = False,
    context: _Dynamic | None = None,
    config: _Dynamic | None = None,
    turn_index: int = 0,
) -> _LangChainAdaptedAgent:
    """
    Wrap a LangGraph compiled graph (or compatible runnable with ``astream``).

    ``initial_input_factory`` maps the user message string to the input dict
    passed to ``astream``. Use ``context`` / ``config`` for LangGraph runtime
    data (or pass callables ``str -> value`` for per-turn values). Use
    ``stream_mode``, ``version``, and ``subgraphs`` for streaming behavior.
    """
    return _LangChainAdaptedAgent(
        graph,
        initial_input_factory,
        stream_mode=stream_mode,
        version=version,
        subgraphs=subgraphs,
        context=context,
        config=config,
        turn_index=turn_index,
    )


__all__ = ["wrap_langchain_agent"]
