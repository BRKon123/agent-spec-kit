"""
Scenario-facing run contract: one user message in, normalized events + output out.

Custom framework integration (CrewAI, etc.)
------------------------------------------

Implement :class:`AdaptedAgent` and return :class:`TurnResult` from
:meth:`AdaptedAgent.run_turn`. Populate ``events`` with the typed classes in
:mod:`agent_spec_kit.events` (not ad-hoc dicts):

1. **AgentTurnEvent** (root) — created at turn start; holds ``children`` (nested
   ``ToolCallEvent`` and optional subgraph ``AgentTurnEvent`` nodes). Set
   ``user_input`` and ``agent_output`` when the root turn completes.
2. **ToolCallEvent** — tool calls as children of the root turn or of another tool
   when execution nests; set ``tool_name``, ``args``, ``result`` or ``error``.

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
