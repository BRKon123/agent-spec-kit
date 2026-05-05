"""Fuzz strategies and helpers (``import agent_spec_kit as ek; ek.fuzz``)."""

from __future__ import annotations

from agent_spec_kit.fuzz_types import GeneratedTurn, Strategy
from agent_spec_kit.fuzz.behaviour_grammar import behaviour_grammar
from agent_spec_kit.fuzz.hybrid import hybrid
from agent_spec_kit.fuzz.llm_mutations import llm_mutations
from agent_spec_kit.fuzz_config import UserAction


def user_action(
    name: str,
    templates: tuple[str, ...] | list[str],
    *,
    tags: tuple[str, ...] | list[str] = (),
    weight: float = 1.0,
    metadata: dict[str, object] | None = None,
) -> UserAction:
    """Build a :class:`~agent_spec_kit.fuzz_config.UserAction` for behaviour_grammar."""
    t = tuple(templates) if isinstance(templates, list) else templates
    tg = tuple(tags) if isinstance(tags, list) else tags
    return UserAction(name=name, templates=t, tags=tg, weight=weight, metadata=dict(metadata or {}))


__all__ = [
    "GeneratedTurn",
    "Strategy",
    "UserAction",
    "behaviour_grammar",
    "hybrid",
    "llm_mutations",
    "user_action",
]
