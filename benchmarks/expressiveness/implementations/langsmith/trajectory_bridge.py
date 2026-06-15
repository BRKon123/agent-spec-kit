"""Harness: map frozen expressiveness traces to agentevals message trajectories."""

from __future__ import annotations

import json
from typing import Any


def trace_to_messages(trace: dict[str, Any], *, turn: str | None = None) -> list[dict[str, Any]]:
    """Build an agentevals/OpenAI-style message list from a frozen trace dict."""
    if turn == "last":
        turns = trace.get("turns") or []
        tools = (turns[-1].get("tools") or []) if turns else []
    else:
        tools = list(trace.get("tools") or [])

    tool_calls = [
        {
            "function": {
                "name": str(t.get("name", "")),
                "arguments": json.dumps(t.get("args") or {}),
            }
        }
        for t in tools
    ]
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "check"},
        {"role": "assistant", "content": "", "tool_calls": tool_calls},
    ]
    for _ in tools:
        messages.append({"role": "tool", "content": "ok"})
    messages.append({"role": "assistant", "content": str(trace.get("output", ""))})
    return messages


def reference_messages_for_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return trace_to_messages({"tools": tools, "output": ""})
