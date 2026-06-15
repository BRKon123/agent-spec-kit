"""LLM-based transcript mutation for the telecom fuzzing study."""

from __future__ import annotations

import os
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from agent_spec_kit.fuzz_types import FuzzSegmentContext, GeneratedTurn, Strategy
from agent_spec_kit.judges.structured import call_structured

DEFAULT_FUZZ_MUTATION_MODEL = "openai:gpt-5-nano"

MUTATION_INTENTS: dict[str, str] = {
    "drop_required_fact": (
        "Remove or omit account ids, verification tokens, and line ids from the opening user turn "
        "while keeping the customer's underlying request."
    ),
    "delay_required_fact": (
        "Move a fact that appears in a later user turn to an earlier turn, so required information "
        "arrives sooner in the dialogue."
    ),
    "swap_entity": (
        "Swap correct and stale line identifiers in the transcript so the user initially names the "
        "wrong line."
    ),
    "contradict_entity_later": (
        "After an earlier mention of a wrong line or account id, append a user correction that "
        "clarifies the intended line or account."
    ),
    "negate_completed_step": (
        "Add a user turn denying they completed a troubleshooting or restart step they previously "
        "claimed to have done."
    ),
    "ambiguous_acknowledgement": (
        "Make the final user acknowledgement vague or non-committal while keeping the rest of the "
        "dialogue intact."
    ),
    "remove_confirmation": (
        "Remove explicit yes/confirm/go-ahead phrasing from user turns while preserving intent."
    ),
    "increase_pressure": (
        "Append a user demand for escalation, refund, immediate shipment, or faster resolution."
    ),
    "interleave_secondary_intent": (
        "Insert a secondary billing or line issue into the middle of the dialogue."
    ),
    "third_party_shift": (
        "Reframe the issue as belonging to another person's line rather than the caller's own line."
    ),
    "temporary_address_shift": (
        "Add a user request to ship to an unverified temporary address."
    ),
    "repeat_or_reorder_turn": (
        "Repeat an early user turn or swap the order of two user turns to create sequencing stress."
    ),
    "minimise_user_replies": (
        "Shorten each user reply to terse, vague fragments while keeping the same number of turns."
    ),
    "over_specific_false_detail": (
        "Add plausible but false ticket references or timestamps to the opening user turn."
    ),
    "policy_boundary_shift": (
        "Append an aggressive compensation demand that pushes against stated policy limits."
    ),
}

DYNAMIC_OPERATORS = frozenset(
    {
        "contradict_entity_later",
        "negate_completed_step",
        "repeat_or_reorder_turn",
    }
)


class _TranscriptMutationResponse(BaseModel):
    messages: list[str] = Field(default_factory=list, min_length=1)


def ensure_openai_api_key() -> None:
    key = os.environ.get("OPENAI_API_KEY", "").strip() or os.environ.get("OPENAI_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "LLM fuzz mutations require OPENAI_API_KEY (or OPENAI_KEY) in the environment."
        )
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        os.environ["OPENAI_API_KEY"] = key


def _intent_prompt(operator_id: str) -> str:
    if operator_id not in MUTATION_INTENTS:
        raise ValueError(f"unknown mutation intent: {operator_id}")
    return MUTATION_INTENTS[operator_id]


def _context_block(context: FuzzSegmentContext | None) -> str:
    if context is None:
        return "Dialogue segment: opening segment (no prior agent turns in this segment)."
    lines = [
        f"Dialogue segment index: {context.segment_index}.",
        "Prior user messages in this conversation:",
    ]
    for i, msg in enumerate(context.prior_user_messages, start=1):
        lines.append(f"  U{i}: {msg!r}")
    lines.append("Prior agent messages:")
    for i, msg in enumerate(context.prior_agent_messages, start=1):
        lines.append(f"  A{i}: {msg!r}")
    if context.prior_tool_names:
        lines.append(f"Prior agent tools: {', '.join(context.prior_tool_names)}")
    return "\n".join(lines)


def _build_user_prompt(
    *,
    seed_inputs: tuple[str, ...],
    intents: tuple[str, ...],
    context: FuzzSegmentContext | None,
    seed_meta: dict[str, Any],
) -> str:
    transcript = "\n".join(f"{i + 1}. {msg!r}" for i, msg in enumerate(seed_inputs))
    intent_text = "\n".join(f"- {intent}" for intent in intents)
    meta_bits = []
    for key in ("customer_id", "line_id", "line_id_2", "stale_line_id"):
        if key in seed_meta:
            meta_bits.append(f"{key}={seed_meta[key]!r}")
    meta_line = ", ".join(meta_bits) if meta_bits else "(none)"
    return (
        f"{_context_block(context)}\n\n"
        f"Scenario metadata: {meta_line}\n\n"
        "Seed user transcript for this segment:\n"
        f"{transcript}\n\n"
        "Apply these mutation intents in order:\n"
        f"{intent_text}\n\n"
        f"Return exactly {len(seed_inputs)} mutated user messages in the same order. "
        "Keep messages plausible as real mobile-support chat. "
        "Do not add assistant text. "
        'Return strict JSON: {"messages": ["...", ...]} with one string per user turn.'
    )


async def mutate_transcript_with_llm(
    *,
    seed_inputs: tuple[str, ...],
    operator_id: str,
    composition: tuple[str, ...],
    seed_meta: dict[str, Any],
    context: FuzzSegmentContext | None,
    model: str,
    temperature: float | None,
    timeout_s: float | None,
) -> list[str]:
    if not seed_inputs:
        return []
    ensure_openai_api_key()
    intents = (_intent_prompt(operator_id),) + tuple(_intent_prompt(op) for op in composition)
    parsed = await call_structured(
        model=model,
        system=(
            "You rewrite customer-support user transcripts for fuzz testing. "
            "Apply the requested mutation intents faithfully. Output JSON only."
        ),
        user=_build_user_prompt(
            seed_inputs=seed_inputs,
            intents=intents,
            context=context,
            seed_meta=seed_meta,
        ),
        response_model=_TranscriptMutationResponse,
        temperature=temperature,
        timeout_s=timeout_s,
    )
    if len(parsed.messages) != len(seed_inputs):
        raise RuntimeError(
            f"llm mutation returned {len(parsed.messages)} messages, expected {len(seed_inputs)}"
        )
    out = [str(m).strip() for m in parsed.messages]
    if any(not m for m in out):
        raise RuntimeError("llm mutation returned an empty user message")
    return out


@dataclass(frozen=True, slots=True)
class LLMMutationOperatorStrategy:
    """Fuzz strategy that mutates seed transcripts via structured LLM calls."""

    operator_id: str
    seed_meta: dict[str, Any]
    model: str = DEFAULT_FUZZ_MUTATION_MODEL
    temperature: float | None = 0.7
    timeout_s: float | None = 120.0
    composition: tuple[str, ...] = ()
    eager_generation: bool = field(init=False)

    def __post_init__(self) -> None:
        dynamic = self.operator_id in DYNAMIC_OPERATORS or bool(self.composition)
        object.__setattr__(self, "eager_generation", not dynamic)

    async def generate(
        self,
        *,
        rng: random.Random,
        max_user_turns: int,
        seed_inputs: tuple[str, ...],
        context: FuzzSegmentContext | None = None,
    ) -> Sequence[GeneratedTurn]:
        _ = rng, max_user_turns
        msgs = await mutate_transcript_with_llm(
            seed_inputs=seed_inputs,
            operator_id=self.operator_id,
            composition=self.composition,
            seed_meta=self.seed_meta,
            context=context,
            model=self.model,
            temperature=self.temperature,
            timeout_s=self.timeout_s,
        )
        detail = {
            "operator": self.operator_id,
            "composition": self.composition,
            "segment_index": context.segment_index if context else 0,
            "model": self.model,
            "mutation_backend": "llm",
        }
        return tuple(
            GeneratedTurn(
                message=m,
                label=f"llm_{self.operator_id}:{i}",
                detail=detail,
            )
            for i, m in enumerate(msgs)
            if m.strip()
        )


def llm_mutation_operator_strategy(
    *,
    operator_id: str,
    seed_meta: dict[str, Any],
    composition: Sequence[str] = (),
    model: str = DEFAULT_FUZZ_MUTATION_MODEL,
    temperature: float | None = 0.7,
    timeout_s: float | None = 120.0,
) -> LLMMutationOperatorStrategy:
    return LLMMutationOperatorStrategy(
        operator_id=operator_id,
        seed_meta=dict(seed_meta),
        composition=tuple(composition),
        model=model,
        temperature=temperature,
        timeout_s=timeout_s,
    )


__all__ = [
    "DYNAMIC_OPERATORS",
    "DEFAULT_FUZZ_MUTATION_MODEL",
    "LLMMutationOperatorStrategy",
    "MUTATION_INTENTS",
    "ensure_openai_api_key",
    "llm_mutation_operator_strategy",
    "mutate_transcript_with_llm",
]
