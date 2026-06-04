"""Build Promptfoo trajectory spans from frozen expressiveness traces (harness only)."""

from __future__ import annotations

import json
from typing import Any


def _tool_span(tool: dict[str, Any], *, start: int) -> dict[str, Any]:
    args = tool.get("args") or {}
    return {
        "name": str(tool.get("name", "")),
        "startTime": start,
        "endTime": start + 1,
        "attributes": {
            "tool.name": str(tool.get("name", "")),
            "ai.toolCall.name": str(tool.get("name", "")),
            "ai.toolCall.args": json.dumps(args),
        },
    }


def frozen_trace_to_promptfoo_trace(trace: dict[str, Any], check_id: str) -> dict[str, Any]:
    """Normalize frozen JSON traces into Promptfoo ``context.trace`` span lists."""
    if check_id == "C12":
        turns = trace.get("turns") or []
        tools = (turns[-1].get("tools") or []) if turns else []
    else:
        tools = trace.get("tools") or []

    spans: list[dict[str, Any]] = []
    t = 0
    for tool in tools:
        spans.append(_tool_span(tool, start=t))
        t += 2
        for child in tool.get("children") or []:
            spans.append(_tool_span(child, start=t))
            t += 2
    return {"spans": spans}
