"""Shrink passes (``import agent_spec_kit as ek; ek.shrink``)."""

from __future__ import annotations

from agent_spec_kit.fuzz_config import ShrinkPassSpec


def remove_user_turns() -> ShrinkPassSpec:
    """Delta-debug style removal of user turns (activated with ``--shrink``)."""
    return ShrinkPassSpec(kind="remove_user_turns", params={})


def simplify_user_messages() -> ShrinkPassSpec:
    """Deterministic text simplifiers per message."""
    return ShrinkPassSpec(kind="simplify_user_messages", params={})


def llm_semantic_simplify(
    *,
    model: str,
    candidates_per_message: int = 5,
    temperature: float | None = None,
    timeout_s: float | None = None,
) -> ShrinkPassSpec:
    """LLM proposes shorter messages; framework verifies reproduction."""
    return ShrinkPassSpec(
        kind="llm_semantic_simplify",
        params={
            "model": model,
            "candidates_per_message": candidates_per_message,
            "temperature": temperature,
            "timeout_s": timeout_s,
        },
    )


__all__ = ["llm_semantic_simplify", "remove_user_turns", "simplify_user_messages"]
