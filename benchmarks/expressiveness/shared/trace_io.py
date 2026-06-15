"""Load frozen traces and build TurnResult for scripted agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.run import TurnResult

from shared.paths import trace_path


def load_trace(check_id: str, *, directory: Path | None = None) -> dict[str, Any]:
    root = directory if directory is not None else trace_path(check_id).parent
    p = root / f"{check_id}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def save_trace(
    check_id: str, data: dict[str, Any], *, directory: Path | None = None
) -> Path:
    root = directory if directory is not None else trace_path(check_id).parent
    p = root / f"{check_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    return p


def _tool_dict_to_event(tool: dict[str, Any]) -> ToolCallEvent:
    children: list[ToolCallEvent] = []
    for ch in tool.get("children") or []:
        if isinstance(ch, dict):
            children.append(_tool_dict_to_event(ch))
    return ToolCallEvent(
        tool_name=str(tool.get("name", "")),
        args=tool.get("args"),
        result=tool.get("result"),
        error=tool.get("error"),
        children=children,
        metadata=dict(tool.get("metadata") or {}),
    )


def turn_result_from_trace(trace: dict[str, Any], *, user_message: str = "") -> TurnResult:
    root = AgentTurnEvent(user_input=user_message or "(scripted)")
    for tool in trace.get("tools") or []:
        if isinstance(tool, dict):
            root.children.append(_tool_dict_to_event(tool))
    output = trace.get("output", "")
    root.agent_output = output
    return TurnResult(output=output, events=(root,))


def turn_results_from_multitrace(trace: dict[str, Any]) -> list[TurnResult]:
    turns = trace.get("turns") or []
    out: list[TurnResult] = []
    for i, t in enumerate(turns):
        if isinstance(t, dict):
            out.append(turn_result_from_trace(t, user_message=f"turn-{i}"))
    return out
