"""Fuzz strategy protocol and generated-turn types (top-level to avoid import cycles)."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

@dataclass(frozen=True, slots=True)
class FuzzSegmentContext:
    """Transcript state visible when generating a later fuzz segment."""

    segment_index: int
    prior_user_messages: tuple[str, ...]
    prior_agent_messages: tuple[str, ...]
    prior_tool_names: tuple[str, ...]
    last_checkpoint_passed: bool | None = None


@dataclass(frozen=True, slots=True)
class GeneratedTurn:
    """One generated user line with deterministic labels for UI / storage."""

    message: str
    label: str
    detail: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Strategy(Protocol):
    """Async fuzz strategy: produces labelled user turns."""

    async def generate(
        self,
        *,
        rng: random.Random,
        max_user_turns: int,
        seed_inputs: tuple[str, ...],
        context: FuzzSegmentContext | None = None,
    ) -> Sequence[GeneratedTurn]:
        ...


__all__ = ["FuzzSegmentContext", "GeneratedTurn", "Strategy"]
