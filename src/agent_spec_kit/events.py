"""Framework-neutral normalized agent events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, TypeAlias


def new_event_id(*, prefix: str = "") -> str:
    """Return a new opaque event id, optionally prefixed for debugging."""
    u = uuid.uuid4().hex
    return f"{prefix}{u}" if prefix else u


@dataclass(frozen=True, slots=True)
class BaseEvent:
    """Shared fields for all tracked agent events."""

    turn_index: int | None = None
    event_id: str | None = None
    parent_id: str | None = None
    source_path: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolCallEvent(BaseEvent):
    """One tool invocation with a result or error."""

    tool_name: str = ""
    args: Any = None
    result: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AgentTurnEvent(BaseEvent):
    """One agent response to one user message (completed turn)."""

    user_input: Any = None
    agent_output: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SubagentCallEvent(BaseEvent):
    """One nested agent invocation with an output or error."""

    agent_name: str = ""
    call_input: Any = None
    call_output: Any = None
    error: str | None = None


AgentEvent: TypeAlias = ToolCallEvent | AgentTurnEvent | SubagentCallEvent

__all__ = [
    "AgentEvent",
    "AgentTurnEvent",
    "BaseEvent",
    "SubagentCallEvent",
    "ToolCallEvent",
    "new_event_id",
]
