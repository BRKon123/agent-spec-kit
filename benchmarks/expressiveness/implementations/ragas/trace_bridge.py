"""Harness: map frozen expressiveness traces to Ragas message + ToolCall lists."""

from __future__ import annotations

from typing import Any

from ragas.messages import AIMessage, HumanMessage, ToolCall, ToolMessage


def tools_from_trace(trace: dict[str, Any], *, turn: str | None = None) -> list[dict[str, Any]]:
    if turn == "last":
        turns = trace.get("turns") or []
        return list((turns[-1].get("tools") or []) if turns else [])
    return list(trace.get("tools") or [])


def tool_calls_from_trace(trace: dict[str, Any], *, turn: str | None = None) -> list[ToolCall]:
    return [
        ToolCall(name=str(t.get("name", "")), args=dict(t.get("args") or {}))
        for t in tools_from_trace(trace, turn=turn)
    ]


def user_input_from_trace(trace: dict[str, Any], *, turn: str | None = None) -> list[Any]:
    """Build Ragas conversation messages with tool calls from a frozen trace."""
    tools = tools_from_trace(trace, turn=turn)
    messages: list[Any] = [HumanMessage(content="check")]
    if tools:
        messages.append(
            AIMessage(
                content="",
                tool_calls=[
                    ToolCall(name=str(t.get("name", "")), args=dict(t.get("args") or {}))
                    for t in tools
                ],
            )
        )
        for _ in tools:
            messages.append(ToolMessage(content="ok"))
    messages.append(AIMessage(content=str(trace.get("output", ""))))
    return messages


def reference_tool_calls(names: list[str], args: list[dict[str, Any]] | None = None) -> list[ToolCall]:
    arg_list = args or [{} for _ in names]
    return [ToolCall(name=n, args=a) for n, a in zip(names, arg_list, strict=True)]


def specialist_result(trace: dict[str, Any], name: str) -> Any:
    for t in trace.get("tools") or []:
        if t.get("name") == name:
            return t.get("result")
    return None
