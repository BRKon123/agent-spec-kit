"""Hardcoded agent returning canned tool traces for tool-error message demos."""

from __future__ import annotations

import agent_spec_kit as ek
from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.run import TurnResult


def _tool(
    name: str,
    *,
    args: dict | None = None,
    result: str = "ok",
    children: list[ToolCallEvent] | None = None,
) -> ToolCallEvent:
    return ToolCallEvent(
        tool_name=name,
        args=dict(args or {}),
        result=result,
        children=list(children or []),
    )


def _trace_auth_order() -> list[ToolCallEvent]:
    return [
        _tool("authenticate_customer", args={"phone": "555-0100"}),
        _tool(
            "order_replacement_sim",
            args={"line_id": "LINE-002", "address_id": "ADDR-9"},
        ),
    ]


def _trace_auth_only() -> list[ToolCallEvent]:
    return [_tool("authenticate_customer", args={"phone": "555-0100"})]


def _trace_order_with_sim_type() -> list[ToolCallEvent]:
    return [
        _tool(
            "order_replacement_sim",
            args={"line_id": "LINE-002", "sim_type": "esim", "address_id": "ADDR-9"},
        ),
    ]


def _trace_order_line_id_only() -> list[ToolCallEvent]:
    return [_tool("order_replacement_sim", args={"line_id": "LINE-002"})]


def _trace_nested_forensics() -> list[ToolCallEvent]:
    return [
        _tool(
            "run_forensics_specialist",
            args={"query": "latency spike"},
            children=[
                _tool("pull_logs", args={"window_minutes": 15}),
                _tool("score_anomaly", args={"source": "logs", "anomaly_score": 0.72}),
            ],
        ),
    ]


def _trace_five_tools() -> list[ToolCallEvent]:
    return [
        _tool("authenticate_customer"),
        _tool("get_line_status", args={"line_id": "LINE-001"}),
        _tool("send_troubleshooting_step", args={"step": 1}),
        _tool("send_troubleshooting_step", args={"step": 2}),
        _tool("close_ticket"),
    ]


def _trace_with_credit() -> list[ToolCallEvent]:
    return [
        _tool("authenticate_customer"),
        _tool("apply_account_credit", args={"amount": 25}),
    ]


class _ToolTraceAgent:
    async def run_turn(self, user_message: str) -> TurnResult:
        msg = user_message.lower()
        if "trace:auth-order" in msg:
            tools = _trace_auth_order()
        elif "trace:auth-only" in msg:
            tools = _trace_auth_only()
        elif "trace:order-sim-type" in msg:
            tools = _trace_order_with_sim_type()
        elif "trace:order-line-only" in msg:
            tools = _trace_order_line_id_only()
        elif "trace:nested-forensics" in msg:
            tools = _trace_nested_forensics()
        elif "trace:five-tools" in msg:
            tools = _trace_five_tools()
        elif "trace:with-credit" in msg:
            tools = _trace_with_credit()
        else:
            tools = _trace_auth_order()

        output = f"completed {len(tools)} tool(s)"
        return TurnResult(
            output=output,
            events=(
                AgentTurnEvent(
                    user_input=user_message,
                    agent_output=output,
                    children=tools,
                ),
            ),
        )


@ek.fixture
async def adapted_agent():
    return _ToolTraceAgent()
