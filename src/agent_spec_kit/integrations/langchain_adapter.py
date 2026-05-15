"""
LangChain / LangGraph: :func:`wrap_langchain_agent` streams ``astream`` updates
and maps them to typed events (see :mod:`agent_spec_kit.events`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agent_spec_kit.events import AgentEvent, AgentTurnEvent, ToolCallEvent, new_event_id
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


class UpdatesNormalizer:
    """State machine over LangGraph ``updates`` stream chunks; mutates ``root_turn``."""

    __slots__ = (
        "_root_turn",
        "_first_human",
        "_emitted_tools",
        "_open_stack",
        "_tid_to_node",
        "_last_ai_by_ns",
        "_pending_root_error",
        "_pending_sub_errors",
        "_turn_index",
    )

    def __init__(self, root_turn: AgentTurnEvent, turn_index: int = 0) -> None:
        self._root_turn = root_turn
        self._turn_index = turn_index
        self._first_human: Any = None
        self._emitted_tools: set[str] = set()
        self._open_stack: list[tuple[str, ToolCallEvent]] = []
        self._tid_to_node: dict[str, ToolCallEvent] = {}
        self._last_ai_by_ns: dict[tuple[str, ...], AIMessage] = {}
        self._pending_root_error: str | None = None
        self._pending_sub_errors: dict[tuple[str, ...], str] = {}

    def feed(
        self,
        source_path: tuple[str, ...],
        updates: Mapping[str, Any],
    ) -> None:
        for _node_name, partial in updates.items():
            if not isinstance(partial, dict):
                continue
            messages = partial.get("messages")
            if not isinstance(messages, list):
                continue
            for msg in messages:
                if not isinstance(msg, BaseMessage):
                    continue
                self._feed_message(source_path, msg)

    def _attachment_parent(self) -> AgentTurnEvent | ToolCallEvent:
        if not self._open_stack:
            return self._root_turn
        return self._open_stack[-1][1]

    def _feed_message(
        self,
        source_path: tuple[str, ...],
        msg: BaseMessage,
    ) -> None:
        if isinstance(msg, HumanMessage) and self._first_human is None:
            self._first_human = _message_text(msg)

        if isinstance(msg, AIMessage):
            if getattr(msg, "tool_calls", None):
                parent = self._attachment_parent()
                for tc in msg.tool_calls or []:
                    if not isinstance(tc, dict):
                        continue
                    tid = tc.get("id")
                    if tid is None:
                        continue
                    name = tc.get("name") or ""
                    args = tc.get("args")
                    meta: dict[str, Any] = {}
                    if tid:
                        meta["tool_call_id"] = tid
                    node = ToolCallEvent(
                        turn_index=self._turn_index,
                        event_id=new_event_id(prefix="tool:"),
                        source_path=source_path,
                        metadata=meta,
                        tool_name=name,
                        args=args,
                        result=None,
                        error=None,
                    )
                    parent.children.append(node)
                    self._open_stack.append((tid, node))
                    self._tid_to_node[tid] = node
            else:
                self._last_ai_by_ns[source_path] = msg
                err = _error_from_message(msg)
                if source_path:
                    if err:
                        self._pending_sub_errors[source_path] = err
                else:
                    if err:
                        self._pending_root_error = err
            return

        if isinstance(msg, ToolMessage):
            tid = msg.tool_call_id or ""
            if tid and tid in self._emitted_tools:
                return
            pending = self._tid_to_node.get(tid)
            name = msg.name or ""
            err = _error_from_message(msg)
            if pending is None:
                tm_meta: dict[str, Any] = {}
                if tid:
                    tm_meta["tool_call_id"] = tid
                parent = self._attachment_parent()
                orphan = ToolCallEvent(
                    turn_index=self._turn_index,
                    event_id=new_event_id(prefix="tool:"),
                    source_path=source_path,
                    metadata=tm_meta,
                    tool_name=name,
                    args=None,
                    result=None if err else msg.content,
                    error=err,
                )
                parent.children.append(orphan)
            else:
                if not pending.tool_name and name:
                    pending.tool_name = name
                pending.result = None if err else msg.content
                pending.error = err
                self._open_stack = [(t, n) for t, n in self._open_stack if t != tid]
                if tid:
                    self._tid_to_node.pop(tid, None)
            if tid:
                self._emitted_tools.add(tid)
            return

    def finalize(self) -> None:
        root_ai = self._last_ai_by_ns.get(())
        self._root_turn.user_input = self._first_human
        if root_ai is not None:
            self._root_turn.agent_output = _message_text(root_ai)
            self._root_turn.error = self._pending_root_error
        for ns, ai in self._last_ai_by_ns.items():
            if not ns:
                continue
            name = ns[-1] if ns else "subagent"
            err = self._pending_sub_errors.get(ns)
            sub_turn = AgentTurnEvent(
                turn_index=self._turn_index,
                event_id=new_event_id(prefix="turn:"),
                source_path=ns,
                metadata={"subgraph_node": name},
                user_input=None,
                agent_output=_message_text(ai),
                error=err,
            )
            self._root_turn.children.append(sub_turn)


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
    """``agent_output`` from the root ``AgentTurnEvent`` (``source_path == ()``), if any."""
    if not events:
        return None
    head = events[0]
    if isinstance(head, AgentTurnEvent) and head.source_path == ():
        return head.agent_output
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
        root_turn = AgentTurnEvent(
            turn_index=self._turn_index,
            event_id=new_event_id(prefix="turn:"),
            source_path=(),
            metadata={},
            user_input=None,
            agent_output=None,
            error=None,
        )
        try:
            inp = self._initial_input_factory(user_message)
            cfg = _resolve_dynamic(self._config, user_message)
            ctx = _resolve_dynamic(self._context, user_message)
            norm = UpdatesNormalizer(root_turn, turn_index=self._turn_index)
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
                    norm.feed(ns, {node_name: partial})
            norm.finalize()
            out = root_turn_output((root_turn,))
            return TurnResult(
                output=out,
                events=(root_turn,),
                status="ok",
                error=None,
            )
        except Exception as e:
            err = str(e)
            root_turn.error = err
            return TurnResult(
                output=None,
                events=(root_turn,),
                status="error",
                error=err,
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
