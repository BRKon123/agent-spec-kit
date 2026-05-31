"""Build :class:`FuzzSegmentContext` from live scenario transcripts."""

from __future__ import annotations

from typing import Any

from agent_spec_kit.fuzz_types import FuzzSegmentContext
from agent_spec_kit.run import ConversationTurn
from agent_spec_kit.scenario_core import tool_dicts_from_turn_data


def strategy_eager_generation(strategy: object) -> bool:
    """True if the strategy pre-generates all turns (probe may bake messages early)."""
    return bool(getattr(strategy, "eager_generation", True))


def _flatten_tool_names(tool_dict: dict[str, Any]) -> list[str]:
    name = str(tool_dict.get("name", "")).strip()
    children = tool_dict.get("children") or []
    if not children:
        return [name] if name else []
    child_parts: list[str] = []
    for ch in children:
        if isinstance(ch, dict):
            child_parts.extend(_flatten_tool_names(ch))
    if name:
        return [f"{name}[{' -> '.join(child_parts)}]"] if child_parts else [name]
    return child_parts


def build_fuzz_segment_context(
    turn_results: tuple[ConversationTurn, ...],
    *,
    segment_index: int,
    last_checkpoint_passed: bool | None = None,
) -> FuzzSegmentContext:
    user_msgs: list[str] = []
    agent_msgs: list[str] = []
    tool_names: list[str] = []
    for turn in turn_results:
        actor = getattr(turn, "actor", None)
        if actor == "user":
            raw = getattr(turn, "text", None) or getattr(turn, "output", None)
            text = (raw if isinstance(raw, str) else str(raw) if raw is not None else "").strip()
            if text:
                user_msgs.append(text)
        elif actor == "agent":
            raw = getattr(turn, "text", None) or getattr(turn, "output", None)
            text = (raw if isinstance(raw, str) else str(raw) if raw is not None else "").strip()
            if text:
                agent_msgs.append(text)
            for td in tool_dicts_from_turn_data(turn):
                tool_names.extend(_flatten_tool_names(td))
    return FuzzSegmentContext(
        segment_index=segment_index,
        prior_user_messages=tuple(user_msgs),
        prior_agent_messages=tuple(agent_msgs),
        prior_tool_names=tuple(tool_names),
        last_checkpoint_passed=last_checkpoint_passed,
    )


__all__ = [
    "FuzzSegmentContext",
    "build_fuzz_segment_context",
    "strategy_eager_generation",
]
