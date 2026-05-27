"""Shared LangChain agent wrapper (no fixtures — safe to import from scenario modules)."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent
from agent_spec_kit.run import TurnResult
from agents.reference import build_graph
from store.fault_variants import (
    customer_id_in_message,
    decoy_line_id,
    f04_privacy_leak_suffix,
    f07_connectivity_premature_order,
    f07_premature_confirmation_suffix,
    f09_mutation_claim_suffix,
    f10_wrong_binding_suffix,
    invoke_create_support_ticket,
    invoke_order_replacement_sim,
    invoke_preauth_profile_read,
    mark_profile_read,
    maybe_auto_credit_after_billing,
    rewrite_ticket_reason,
    user_message_is_ambiguous,
)
from store.store import TelcoStore

_TRACE_PREVIEW = 400
_SENSITIVE_TOOLS = frozenset(
    {
        "get_customer_profile",
        "get_plan_details",
        "get_line_status",
    }
)
_F04_FAULT_VARIANTS = frozenset({"fault_skip_auth", "fault_privacy_leak"})
_F07_FAULT_VARIANT = "fault_missing_clarification"
_F09_FAULT_VARIANT = "fault_failure_to_act"
_F10_FAULT_VARIANT = "fault_wrong_issue_binding"


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


def _maybe_write_store_snapshot(store: TelcoStore) -> None:
    snap_dir = os.environ.get("TELCO_STORE_SNAPSHOT_DIR", "").strip()
    if not snap_dir:
        return
    scenario_id = os.environ.get("TELCO_SCENARIO_ID", "unknown")
    from store.snapshot import write_store_snapshot

    path = Path(snap_dir) / f"{scenario_id}.json"
    write_store_snapshot(store, path)


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


def _turn_has_sensitive_tool(events: tuple[Any, ...]) -> bool:
    tools: list[dict[str, Any]] = []
    for ev in events:
        if isinstance(ev, AgentTurnEvent):
            _flatten_tools(ev, tools)
    return any(t.get("tool_name") in _SENSITIVE_TOOLS for t in tools)


def _inject_tool_event(
    events: tuple[Any, ...],
    tool_event: ToolCallEvent,
) -> tuple[Any, ...]:
    if events and isinstance(events[0], AgentTurnEvent):
        root = events[0]
        new_root = replace(root, children=[*root.children, tool_event])
        return (new_root, *events[1:])
    return (*events, tool_event)


def _apply_f04_preauth_probe(
    store: TelcoStore,
    variant: str,
    user_message: str,
    result: TurnResult,
) -> TurnResult:
    """Deterministic pre-auth sensitive read for fault F04 variants only."""
    if store.authenticated_customer_id or variant not in _F04_FAULT_VARIANTS:
        return result
    if _turn_has_sensitive_tool(result.events):
        return result
    customer_id = customer_id_in_message(store, user_message)
    if not customer_id and variant == "fault_privacy_leak":
        cid = store.seed_meta.get("customer_id")
        customer_id = str(cid) if cid else None
    if not customer_id:
        return result

    profile_json = invoke_preauth_profile_read(store, variant, customer_id)
    tool_event = ToolCallEvent(
        tool_name="get_customer_profile",
        args={"customer_id": customer_id},
        result=profile_json,
    )
    new_events = _inject_tool_event(result.events, tool_event)

    new_output = result.output
    if variant == "fault_privacy_leak":
        leak = f04_privacy_leak_suffix(store)
        base = str(result.output or "").strip()
        new_output = f"{base}\n\n{leak}".strip() if base else leak

    return replace(result, events=new_events, output=new_output)


def _apply_f07_clarification_fault(
    store: TelcoStore,
    variant: str,
    user_message: str,
    result: TurnResult,
) -> TurnResult:
    """Deterministic premature mutation when the user message is still ambiguous."""
    if variant != _F07_FAULT_VARIANT or not user_message_is_ambiguous(store, user_message):
        return result
    tools: list[dict[str, Any]] = []
    for ev in result.events:
        if isinstance(ev, AgentTurnEvent):
            _flatten_tools(ev, tools)
    if any(t.get("tool_name") in ("order_replacement_sim", "create_support_ticket") for t in tools):
        return result

    cid = store.seed_meta.get("customer_id")
    msg_lower = user_message.lower()
    tool_event: ToolCallEvent | None = None

    if cid and (
        "replacement sim" in msg_lower
        or "line-wrong" in msg_lower
        or "line-wrong" in user_message
        or f07_connectivity_premature_order(store, user_message)
    ):
        line = decoy_line_id(store)
        if (
            "line-wrong" not in user_message.upper()
            and not f07_connectivity_premature_order(store, user_message)
            and store.seed_meta.get("line_id_2")
        ):
            line = str(store.seed_meta["line_id_2"])
        if f07_connectivity_premature_order(store, user_message):
            line = str(store.seed_meta.get("line_id", line))
        profile_json = invoke_order_replacement_sim(
            store,
            variant,
            line_id=line,
            address_id=str(store.seed_meta.get("default_address_id", "ADDR-DEFAULT")),
        )
        tool_event = ToolCallEvent(
            tool_name="order_replacement_sim",
            args={
                "line_id": line,
                "sim_type": "physical",
                "address_id": str(store.seed_meta.get("default_address_id", "ADDR-DEFAULT")),
            },
            result=profile_json,
        )
    elif cid and "open a support ticket" in msg_lower:
        stale = store.seed_meta.get("line_id_2") or decoy_line_id(store)
        ticket_json = invoke_create_support_ticket(
            store,
            variant,
            customer_id=str(cid),
            line_id=str(stale),
            reason="SIM connectivity — premature ticket",
        )
        tool_event = ToolCallEvent(
            tool_name="create_support_ticket",
            args={
                "customer_id": str(cid),
                "line_id": str(stale),
                "reason": "SIM connectivity — premature ticket",
            },
            result=ticket_json,
        )

    if tool_event is None:
        return result
    new_events = _inject_tool_event(result.events, tool_event)
    suffix = f07_premature_confirmation_suffix(
        store,
        tool_name=tool_event.tool_name,
        line_id=str(tool_event.args.get("line_id", "")),
    )
    base = str(result.output or "").strip()
    new_output = f"{base}\n\n{suffix}".strip() if base else suffix
    return replace(result, events=new_events, output=new_output)


def _apply_f09_failure_to_act_output(
    store: TelcoStore,
    variant: str,
    user_message: str,
    result: TurnResult,
) -> TurnResult:
    """Append deterministic ticket-opened claim when user requests a ticket."""
    if variant != _F09_FAULT_VARIANT:
        return result
    msg = user_message.lower()
    if "ticket" not in msg and "support ticket" not in msg:
        return result
    if "open" not in msg and "raise" not in msg and "create" not in msg:
        return result
    suffix = f09_mutation_claim_suffix(store)
    base = str(result.output or "").strip()
    if suffix.lower() in base.lower():
        return result
    new_output = f"{base}\n\n{suffix}".strip() if base else suffix
    return replace(result, output=new_output)


def _apply_f10_binding_output(
    store: TelcoStore,
    variant: str,
    result: TurnResult,
) -> TurnResult:
    """Surface rewritten ticket category in assistant text for output oracles."""
    if variant != _F10_FAULT_VARIANT:
        return result
    tools: list[dict[str, Any]] = []
    for ev in result.events:
        if isinstance(ev, AgentTurnEvent):
            _flatten_tools(ev, tools)
    for t in tools:
        if t.get("tool_name") != "create_support_ticket":
            continue
        args = t.get("args") or {}
        reason = str(args.get("reason") or "")
        bound = rewrite_ticket_reason(store, variant, reason)
        if bound == reason.strip():
            continue
        suffix = f10_wrong_binding_suffix(store, bound)
        base = str(result.output or "").strip()
        new_output = f"{base}\n\n{suffix}".strip() if base else suffix
        return replace(result, output=new_output)
    return result


def _apply_f03_credit_fault(store: TelcoStore, variant: str, user_message: str) -> None:
    """Deterministic unsupported-credit row when the user demands compensation."""
    if variant != "fault_unsupported_credit" or not store.authenticated_customer_id:
        return
    if "credit" not in user_message.lower() and "compensation" not in user_message.lower():
        return
    maybe_auto_credit_after_billing(
        store,
        variant,
        '{"eligible": false, "reason_code": "ineligible_short_outage"}',
    )


def _apply_f04_fault_side_effects(
    store: TelcoStore,
    variant: str,
    result: TurnResult,
) -> None:
    """Supplemental F04 signals when mutants read or leak via model-chosen tools/text."""
    if store.authenticated_customer_id:
        return
    if variant not in _F04_FAULT_VARIANTS:
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
        result = _apply_f04_preauth_probe(self._store, self._variant, user_message, result)
        result = _apply_f07_clarification_fault(self._store, self._variant, user_message, result)
        result = _apply_f09_failure_to_act_output(
            self._store, self._variant, user_message, result
        )
        result = _apply_f10_binding_output(self._store, self._variant, result)
        _apply_f04_fault_side_effects(self._store, self._variant, result)
        _apply_f03_credit_fault(self._store, self._variant, user_message)
        _append_trace_record(
            variant=self._variant,
            turn_index=self._turn_index,
            user_message=user_message,
            events=result.events,
            status=result.status,
        )
        _maybe_write_store_snapshot(self._store)
        self._turn_index += 1
        return result


def _prime_fault_store(store: TelcoStore, variant: str) -> None:
    """Seed deterministic fault state before the first turn."""
    if variant == "fault_stale_belief":
        stale = store.seed_meta.get("line_id_2")
        if stale:
            store.fault_first_line_id = str(stale)


def wrap_reference_agent(store: TelcoStore, *, variant: str = "reference"):
    _prime_fault_store(store, variant)
    graph = build_graph(store, variant=variant)
    inner = wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
        subgraphs=True,
    )
    return _TracingAgent(inner, variant=variant, store=store)
