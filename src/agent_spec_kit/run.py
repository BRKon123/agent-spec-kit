"""
Scenario-facing run contract: one user message in, normalized events + output out.

Custom framework integration (CrewAI, etc.)
------------------------------------------

Implement :class:`AdaptedAgent` and return :class:`TurnResult` from
:meth:`AdaptedAgent.run_turn`. Populate ``events`` with the typed classes in
:mod:`agent_spec_kit.events` (not ad-hoc dicts):

1. **ToolCallEvent** — when a tool finishes: set ``tool_name``, ``args``,
   ``result`` or ``error``.
2. **AgentTurnEvent** — once per completed **root** turn: ``user_input`` and
   ``agent_output`` (the final assistant reply for that user message).
3. **SubagentCallEvent** — for nested agents when your framework exposes a
   path; set ``source_path`` and ``agent_name`` when possible.

Prefer **coarse** step-level events over token streams for v1. See event
field definitions in :mod:`agent_spec_kit.events`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from agent_spec_kit.events import AgentEvent


@dataclass(frozen=True, slots=True)
class TurnResult:
    """Result of one ``AdaptedAgent.run_turn`` call."""

    output: Any = None
    events: tuple[AgentEvent, ...] = field(default_factory=tuple)
    status: str = "ok"
    error: str | None = None


@runtime_checkable
class AdaptedAgent(Protocol):
    """Minimal contract for scenario tests and custom framework adapters."""

    async def run_turn(self, user_message: str) -> TurnResult:
        """Run one user turn and return normalized events plus final output."""
        ...


__all__ = ["AdaptedAgent", "TurnResult"]
