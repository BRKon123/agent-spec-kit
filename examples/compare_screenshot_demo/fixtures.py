"""Hardcoded support agent for compare-page screenshot demos.

Set ``ASK_COMPARE_VARIANT`` to ``baseline``, ``v1``, or ``v3`` before running::

    ASK_COMPARE_VARIANT=baseline uv run agent-spec-kit run examples/compare_screenshot_demo/ --experiment baseline
"""

from __future__ import annotations

import os

import agent_spec_kit as ek
from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.run import TurnResult

_VARIANT = os.environ.get("ASK_COMPARE_VARIANT", "baseline").strip().lower()

# Per-variant canned replies and tool behaviour for screenshot scenarios.
_VARIANT_PROFILES: dict[str, dict[str, object]] = {
    "baseline": {
        "greeting": "Hello! Welcome to Acme Support. How can I help you today?",
        "order_status": "Your order #48291 is confirmed and will ship tomorrow.",
        "refund_policy": "Refunds are available within 30 days of purchase.",
        "calculate_total": {"tool": "add_line_items", "args": {"items": [19.99, 24.50]}, "result": 44.49},
        "auth_gate": "Please sign in before I can access your account details.",
        "shipping_estimate": "Standard shipping to London takes 3–5 business days.",
    },
    "v1": {
        "greeting": "Hello! Welcome to Acme Support. How can I help you today?",
        "order_status": "Your order #48291 is confirmed and will ship tomorrow.",
        "refund_policy": "Refunds are available within 30 days of purchase.",
        "calculate_total": {"tool": "add_line_items", "args": {"items": [19.99, 24.50]}, "result": 99.99},
        "auth_gate": "Please sign in before I can access your account details.",
        "shipping_estimate": "Standard shipping to London takes 3–5 business days.",
    },
    "v3": {
        "greeting": "Hello! Welcome to Acme Support. How can I help you today?",
        "order_status": "Your order #48291 is confirmed and will ship tomorrow.",
        "refund_policy": "Refunds are available within 7 days of purchase.",
        "calculate_total": {"tool": "add_line_items", "args": {"items": [19.99, 24.50]}, "result": 44.49},
        "auth_gate": "You're signed in. I can see your account now.",
        "shipping_estimate": "Express shipping to London takes 1–2 business days.",
    },
}


def _profile() -> dict[str, object]:
    if _VARIANT not in _VARIANT_PROFILES:
        known = ", ".join(sorted(_VARIANT_PROFILES))
        raise RuntimeError(
            f"Unknown ASK_COMPARE_VARIANT={_VARIANT!r}; expected one of: {known}"
        )
    return _VARIANT_PROFILES[_VARIANT]


class _SupportAgent:
    async def run_turn(self, user_message: str) -> TurnResult:
        msg = user_message.lower()
        profile = _profile()

        if "greet" in msg or "hello" in msg:
            output = str(profile["greeting"])
            return TurnResult(
                output=output,
                events=(AgentTurnEvent(user_input=user_message, agent_output=output),),
            )

        if "order" in msg and "status" in msg:
            output = str(profile["order_status"])
            return TurnResult(
                output=output,
                events=(AgentTurnEvent(user_input=user_message, agent_output=output),),
            )

        if "refund" in msg:
            output = str(profile["refund_policy"])
            return TurnResult(
                output=output,
                events=(AgentTurnEvent(user_input=user_message, agent_output=output),),
            )

        if "total" in msg or "line items" in msg:
            spec = profile["calculate_total"]
            assert isinstance(spec, dict)
            tool_name = str(spec["tool"])
            args = dict(spec["args"])  # type: ignore[arg-type]
            result = spec["result"]
            tool = ToolCallEvent(tool_name=tool_name, args=args, result=result)
            output = f"The cart total is {result}."
            return TurnResult(
                output=output,
                events=(
                    AgentTurnEvent(
                        user_input=user_message,
                        agent_output=output,
                        children=[tool],
                    ),
                ),
            )

        if "account" in msg or "signed in" in msg:
            output = str(profile["auth_gate"])
            return TurnResult(
                output=output,
                events=(AgentTurnEvent(user_input=user_message, agent_output=output),),
            )

        if "shipping" in msg or "delivery" in msg:
            output = str(profile["shipping_estimate"])
            return TurnResult(
                output=output,
                events=(AgentTurnEvent(user_input=user_message, agent_output=output),),
            )

        output = "I'm not sure how to help with that."
        return TurnResult(
            output=output,
            events=(AgentTurnEvent(user_input=user_message, agent_output=output),),
        )


@ek.fixture
async def support_agent():
    return _SupportAgent()
