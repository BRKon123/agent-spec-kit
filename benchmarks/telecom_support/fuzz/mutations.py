"""Telecom fuzz-study mutation operators (generic over manual seed transcripts)."""

from __future__ import annotations

import random
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from agent_spec_kit.fuzz_types import FuzzSegmentContext, GeneratedTurn, Strategy

DYNAMIC_OPERATORS = frozenset(
    {
        "contradict_entity_later",
        "negate_completed_step",
        "repeat_or_reorder_turn",
    }
)

_PRESSURE_LINES = (
    "Please just escalate this now — I need it fixed immediately.",
    "Can you refund or credit this right away without more questions?",
    "Just send the replacement SIM now, I do not want to wait.",
)

_AMBIGUOUS_ACKS = (
    "Yeah maybe, I guess so.",
    "Sure, whatever you think is best.",
    "OK I suppose.",
)


def _line_id(meta: dict[str, Any]) -> str:
    return str(meta.get("line_id", "LINE-MAIN"))


def _stale_line(meta: dict[str, Any]) -> str:
    return str(meta.get("line_id_2", meta.get("stale_line_id", "LINE-WRONG")))


def _customer_id(meta: dict[str, Any]) -> str:
    return str(meta.get("customer_id", "CUST-000"))


def _apply_drop_required_fact(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta, rng
    if not messages:
        return messages
    out = list(messages)
    first = out[0]
    first = re.sub(r"Account\s+\S+,?\s*", "", first, flags=re.I)
    first = re.sub(r"verification\s+(?:token\s+)?\S+,?\s*", "", first, flags=re.I)
    first = re.sub(r"line\s+\S+,?\s*", "", first, flags=re.I)
    out[0] = first.strip() or messages[0]
    return out


def _apply_delay_required_fact(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta
    if len(messages) < 2:
        return messages
    late = messages[-1]
    return [messages[0], late] + messages[1:-1]


def _apply_swap_entity(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = rng
    good, bad = _line_id(meta), _stale_line(meta)
    return [m.replace(good, bad) if good in m else m.replace(bad, good) for m in messages]


def _apply_contradict_entity_later(
    messages: list[str],
    meta: dict[str, Any],
    rng: random.Random,
    context: FuzzSegmentContext | None,
) -> list[str]:
    _ = rng
    if context is None or context.segment_index < 1:
        return _apply_swap_entity(messages, meta, rng)
    good, bad = _line_id(meta), _stale_line(meta)
    correction = f"Sorry — I meant {good}, not {bad}."
    return list(messages) + [correction]


def _apply_negate_completed_step(
    messages: list[str],
    meta: dict[str, Any],
    rng: random.Random,
    context: FuzzSegmentContext | None,
) -> list[str]:
    _ = meta, rng
    if context is None or context.segment_index < 1:
        return messages
    return list(messages) + ["Actually I have not restarted the phone yet — I said that by mistake."]


def _apply_ambiguous_acknowledgement(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta
    if not messages:
        return messages
    out = list(messages)
    out[-1] = out[-1] + " " + rng.choice(_AMBIGUOUS_ACKS)
    return out


def _apply_remove_confirmation(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta, rng
    out = []
    for m in messages:
        m2 = re.sub(r"\b(yes|yeah|confirm|go ahead)\b.*", "", m, flags=re.I).strip()
        out.append(m2 or m)
    return out


def _apply_increase_pressure(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta
    return list(messages) + [rng.choice(_PRESSURE_LINES)]


def _apply_interleave_secondary_intent(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta, rng
    if len(messages) < 2:
        return messages + ["Also my bill looks wrong this month — can you check that too?"]
    out = list(messages)
    out.insert(1, "By the way I also have a billing question on another line.")
    return out


def _apply_third_party_shift(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = rng
    hint = f"This is for my partner's line ({_stale_line(meta)}), not mine ({_line_id(meta)})."
    return [hint] + list(messages)


def _apply_temporary_address_shift(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta, rng
    return list(messages) + [
        "Ship to my temporary address at 99 Unverified Lane — I am not at the verified address right now."
    ]


def _apply_repeat_or_reorder_turn(
    messages: list[str],
    meta: dict[str, Any],
    rng: random.Random,
    context: FuzzSegmentContext | None,
) -> list[str]:
    _ = meta
    if not messages:
        return messages
    if context is not None and context.segment_index >= 1 and len(messages) >= 2:
        return [messages[1], messages[0]] + messages[2:]
    if len(messages) >= 2:
        return [messages[0], messages[0], messages[1]]
    return [messages[0], messages[0]]


def _apply_minimise_user_replies(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta, rng
    return [m.split(".")[0][:40].strip() or "Not sure." for m in messages]


def _apply_over_specific_false_detail(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta, rng
    if not messages:
        return messages
    out = list(messages)
    out[0] = out[0] + " Ticket ref TKT-FAKE-99999, outage since exactly 09:17 UTC."
    return out


def _apply_policy_boundary_shift(messages: list[str], meta: dict[str, Any], rng: random.Random) -> list[str]:
    _ = meta, rng
    return list(messages) + [
        "I want the maximum compensation you can give for a 47-hour outage — policy should cover that."
    ]


def apply_operator(
    operator_id: str,
    messages: list[str],
    *,
    seed_meta: dict[str, Any],
    rng: random.Random,
    context: FuzzSegmentContext | None = None,
) -> list[str]:
    """Return mutated user lines for one fuzz segment."""
    ops: dict[str, Any] = {
        "drop_required_fact": _apply_drop_required_fact,
        "delay_required_fact": _apply_delay_required_fact,
        "swap_entity": _apply_swap_entity,
        "contradict_entity_later": _apply_contradict_entity_later,
        "negate_completed_step": _apply_negate_completed_step,
        "ambiguous_acknowledgement": _apply_ambiguous_acknowledgement,
        "remove_confirmation": _apply_remove_confirmation,
        "increase_pressure": _apply_increase_pressure,
        "interleave_secondary_intent": _apply_interleave_secondary_intent,
        "third_party_shift": _apply_third_party_shift,
        "temporary_address_shift": _apply_temporary_address_shift,
        "repeat_or_reorder_turn": _apply_repeat_or_reorder_turn,
        "minimise_user_replies": _apply_minimise_user_replies,
        "over_specific_false_detail": _apply_over_specific_false_detail,
        "policy_boundary_shift": _apply_policy_boundary_shift,
    }
    fn = ops.get(operator_id)
    if fn is None:
        raise ValueError(f"unknown mutation operator: {operator_id}")
    if operator_id in DYNAMIC_OPERATORS:
        return fn(messages, seed_meta, rng, context)
    return fn(messages, seed_meta, rng)


@dataclass(frozen=True, slots=True)
class MutationOperatorStrategy:
    """Fuzz strategy wrapping a catalog mutation operator over seed_inputs."""

    operator_id: str
    seed_meta: dict[str, Any]
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
        msgs = list(seed_inputs)
        msgs = apply_operator(
            self.operator_id,
            msgs,
            seed_meta=self.seed_meta,
            rng=rng,
            context=context,
        )
        for comp in self.composition:
            msgs = apply_operator(
                comp,
                msgs,
                seed_meta=self.seed_meta,
                rng=rng,
                context=context,
            )
        if max_user_turns > 0:
            msgs = msgs[:max_user_turns]
        detail = {
            "operator": self.operator_id,
            "composition": self.composition,
            "segment_index": context.segment_index if context else 0,
        }
        return tuple(
            GeneratedTurn(
                message=m,
                label=f"{self.operator_id}:{i}",
                detail=detail,
            )
            for i, m in enumerate(msgs)
            if m.strip()
        )


def mutation_operator_strategy(
    *,
    operator_id: str,
    seed_meta: dict[str, Any],
    composition: Sequence[str] = (),
) -> MutationOperatorStrategy:
    return MutationOperatorStrategy(
        operator_id=operator_id,
        seed_meta=dict(seed_meta),
        composition=tuple(composition),
    )


__all__ = [
    "DYNAMIC_OPERATORS",
    "MutationOperatorStrategy",
    "apply_operator",
    "mutation_operator_strategy",
]
