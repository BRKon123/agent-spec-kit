"""Weighted hybrid of multiple fuzz strategies."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Union

from agent_spec_kit.fuzz_types import FuzzSegmentContext, GeneratedTurn, Strategy

_StrategyOrWeighted = Union[Strategy, tuple[Strategy, float]]


@dataclass(frozen=True, slots=True)
class _WeightedStrategy:
    name: str
    strategy: Strategy
    weight: float


class _HybridStrategy:
    __slots__ = ("_parts",)
    eager_generation = True

    def __init__(self, parts: tuple[_WeightedStrategy, ...]) -> None:
        if not parts:
            raise ValueError("hybrid requires at least one strategy")
        if any(p.weight <= 0 for p in parts):
            raise ValueError("hybrid weights must be > 0")
        self._parts = parts

    async def generate(
        self,
        *,
        rng: random.Random,
        max_user_turns: int,
        seed_inputs: tuple[str, ...],
        context: FuzzSegmentContext | None = None,
    ) -> Sequence[GeneratedTurn]:
        _ = context
        total = sum(p.weight for p in self._parts)
        r = rng.random() * total
        acc = 0.0
        chosen = self._parts[0]
        for p in self._parts:
            acc += p.weight
            if r <= acc:
                chosen = p
                break
        inner = await chosen.strategy.generate(
            rng=rng,
            max_user_turns=max_user_turns,
            seed_inputs=seed_inputs,
            context=context,
        )
        return tuple(
            GeneratedTurn(
                message=t.message,
                label=f"{chosen.name}:{t.label}",
                detail={**t.detail, "hybrid_branch": chosen.name},
            )
            for t in inner
        )


def hybrid(*items: _StrategyOrWeighted) -> Strategy:
    """Pick one inner strategy by weight, then delegate ``generate`` to it.

    Each argument is either a ``Strategy`` (weight 1.0) or ``(strategy, weight)``.
    """
    parts: list[_WeightedStrategy] = []
    for i, it in enumerate(items):
        if isinstance(it, tuple):
            strat, w = it[0], float(it[1])
            parts.append(_WeightedStrategy(name=f"b{i}", strategy=strat, weight=w))
        else:
            parts.append(_WeightedStrategy(name=f"b{i}", strategy=it, weight=1.0))
    return _HybridStrategy(tuple(parts))


__all__ = ["hybrid"]
