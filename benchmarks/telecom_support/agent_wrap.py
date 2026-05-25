"""Shared LangChain agent wrapper (no fixtures — safe to import from scenario modules)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent
from agent_spec_kit.run import TurnResult
from agents.reference import build_graph
from store.store import TelcoStore

_TRACE_PREVIEW = 400


def _flatten_tools(node: ToolCallEvent | AgentTurnEvent, out: list[dict[str, Any]]) -> None:
    if isinstance(node, ToolCallEvent):
        preview = node.result
        if isinstance(preview, str) and len(preview) > _TRACE_PREVIEW:
            preview = preview[:_TRACE_PREVIEW] + "…"
        out.append(
            {
                "tool_name": node.tool_name,
                "args": node.args,
                "source_path": list(node.source_path),
                "result_preview": preview,
                "error": node.error,
            }
        )
        for child in node.children:
            if isinstance(child, (ToolCallEvent, AgentTurnEvent)):
                _flatten_tools(child, out)
    elif isinstance(node, AgentTurnEvent):
        for child in node.children:
            if isinstance(child, (ToolCallEvent, AgentTurnEvent)):
                _flatten_tools(child, out)


def _append_trace_record(
    *,
    variant: str,
    turn_index: int,
    user_message: str,
    events: tuple[Any, ...],
    status: str,
) -> None:
    trace_dir = os.environ.get("TELCO_AGENT_TRACE_DIR", "").strip()
    if not trace_dir:
        return
    scenario_id = os.environ.get("TELCO_SCENARIO_ID", "unknown")
    tools: list[dict[str, Any]] = []
    for ev in events:
        if isinstance(ev, AgentTurnEvent):
            _flatten_tools(ev, tools)
    record = {
        "ts": datetime.now(UTC).isoformat(),
        "scenario_id": scenario_id,
        "variant": variant,
        "turn_index": turn_index,
        "user_message": user_message[:500],
        "status": status,
        "tools": tools,
    }
    path = Path(trace_dir) / f"{scenario_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


class _TracingAgent:
    __slots__ = ("_inner", "_variant", "_turn_index")

    def __init__(self, inner: Any, *, variant: str, turn_index: int = 0) -> None:
        self._inner = inner
        self._variant = variant
        self._turn_index = turn_index

    async def run_turn(self, user_message: str) -> TurnResult:
        result = await self._inner.run_turn(user_message)
        _append_trace_record(
            variant=self._variant,
            turn_index=self._turn_index,
            user_message=user_message,
            events=result.events,
            status=result.status,
        )
        return result


def wrap_reference_agent(store: TelcoStore, *, variant: str = "reference"):
    graph = build_graph(store, variant=variant)
    inner = wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
        subgraphs=True,
    )
    return _TracingAgent(inner, variant=variant)
