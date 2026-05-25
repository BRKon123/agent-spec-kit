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
from store.fault_variants import mark_profile_read
from store.store import TelcoStore

_TRACE_PREVIEW = 400
_SENSITIVE_TOOLS = frozenset(
    {
        "get_customer_profile",
        "get_plan_details",
        "get_line_status",
    }
)


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


def _apply_f04_fault_side_effects(
    store: TelcoStore,
    variant: str,
    result: TurnResult,
) -> None:
    """Deterministic F04 signal when mutants read or leak before authentication."""
    if store.authenticated_customer_id:
        return
    if variant not in ("fault_skip_auth", "fault_privacy_leak"):
        return
    tools: list[dict[str, Any]] = []
    for ev in result.events:
        if isinstance(ev, AgentTurnEvent):
            _flatten_tools(ev, tools)
    if any(t.get("tool_name") in _SENSITIVE_TOOLS for t in tools):
        mark_profile_read(store)
        return
    if variant == "fault_skip_auth":
        out = str(result.output or "").lower()
        plan = str(store.seed_meta.get("plan_id") or "").lower()
        if plan and plan in out:
            mark_profile_read(store)
            return
        if any(tok in out for tok in ("your plan is", "you are on", "monthly", "bill amount")):
            mark_profile_read(store)


class _TracingAgent:
    __slots__ = ("_inner", "_variant", "_turn_index", "_store")

    def __init__(
        self,
        inner: Any,
        *,
        variant: str,
        store: TelcoStore,
        turn_index: int = 0,
    ) -> None:
        self._inner = inner
        self._variant = variant
        self._store = store
        self._turn_index = turn_index

    async def run_turn(self, user_message: str) -> TurnResult:
        result = await self._inner.run_turn(user_message)
        _apply_f04_fault_side_effects(self._store, self._variant, result)
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
    return _TracingAgent(inner, variant=variant, store=store)
