"""Hardcoded adapted agent for structured-output scenario examples."""

from __future__ import annotations

import agent_spec_kit as ek
from agent_spec_kit.events import AgentTurnEvent
from agent_spec_kit.run import TurnResult


class _StructuredOutputAgent:
    async def run_turn(self, user_message: str) -> TurnResult:
        payload = {
            "status": "ok",
            "task": "plan_trip",
            "destination": "Lisbon" if "lisbon" in user_message.lower() else "Barcelona",
            "days": 3,
            "itinerary": [
                {"day": 1, "activity": "city walk"},
                {"day": 2, "activity": "museum"},
                {"day": 3, "activity": "food tour"},
            ],
        }
        return TurnResult(
            output=payload,
            events=(AgentTurnEvent(user_input=user_message, agent_output=payload),),
        )


@ek.fixture
async def adapted_agent():
    return _StructuredOutputAgent()
