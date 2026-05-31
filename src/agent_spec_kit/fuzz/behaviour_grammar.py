"""Deterministic behaviour-grammar fuzz strategy."""

from __future__ import annotations

import random
from collections.abc import Sequence

from agent_spec_kit.fuzz_types import FuzzSegmentContext, GeneratedTurn, Strategy
from agent_spec_kit.fuzz_config import UserAction


class _BehaviourGrammarStrategy:
    __slots__ = ("_actions",)
    eager_generation = True

    def __init__(self, actions: tuple[UserAction, ...]) -> None:
        if not actions:
            raise ValueError("behaviour_grammar requires at least one UserAction")
        self._actions = actions

    async def generate(
        self,
        *,
        rng: random.Random,
        max_user_turns: int,
        seed_inputs: tuple[str, ...],
        context: FuzzSegmentContext | None = None,
    ) -> Sequence[GeneratedTurn]:
        _ = context
        if max_user_turns < 1:
            return ()
        weights = [a.weight for a in self._actions]
        total = sum(weights)
        out: list[GeneratedTurn] = []
        for _ in range(max_user_turns):
            r = rng.random() * total
            acc = 0.0
            chosen = self._actions[0]
            for a in self._actions:
                acc += a.weight
                if r <= acc:
                    chosen = a
                    break
            ti = rng.randrange(len(chosen.templates))
            msg = chosen.templates[ti]
            out.append(
                GeneratedTurn(
                    message=msg,
                    label=chosen.name,
                    detail={"template_index": ti},
                )
            )
        return out


def behaviour_grammar(actions: Sequence[UserAction]) -> Strategy:
    """Sample ``UserAction``s weighted by ``weight``; pick a template per turn."""
    acts = tuple(actions)
    return _BehaviourGrammarStrategy(acts)


__all__ = ["behaviour_grammar"]
