"""Agent specification kit — build and validate agent configs."""

from __future__ import annotations

from typing import Any

from agent_spec_kit.events import (
    AgentEvent,
    AgentTurnEvent,
    BaseEvent,
    ToolCallEvent,
    new_event_id,
    print_rich_event_trace,
)
from agent_spec_kit.run import AdaptedAgent, TurnResult

__all__ = [
    "AdaptedAgent",
    "AgentEvent",
    "AgentTurnEvent",
    "BaseEvent",
    "ToolCallEvent",
    "TurnResult",
    "__version__",
    "new_event_id",
    "print_rich_event_trace",
    "wrap_langchain_agent",
    "wrap_pydantic_ai_agent",
]

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name == "wrap_langchain_agent":
        from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

        return wrap_langchain_agent
    if name == "wrap_pydantic_ai_agent":
        from agent_spec_kit.integrations.pydantic_ai_adapter import wrap_pydantic_ai_agent

        return wrap_pydantic_ai_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
