"""LLM-based message mutation fuzz strategy."""

from __future__ import annotations

import random
from collections.abc import Sequence

from pydantic import BaseModel, Field

from agent_spec_kit.fuzz_types import FuzzSegmentContext, GeneratedTurn, Strategy
from agent_spec_kit.judges.structured import call_structured


class _MutationsResponse(BaseModel):
    messages: list[str] = Field(default_factory=list, min_length=1)


class _LLMMutationsStrategy:
    __slots__ = ("_model", "_temperature", "_timeout_s")
    eager_generation = True

    def __init__(
        self,
        *,
        model: str,
        temperature: float | None,
        timeout_s: float | None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._timeout_s = timeout_s

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
        if not seed_inputs:
            raise ValueError("llm_mutations requires non-empty FuzzConfig.seed_inputs")
        out: list[GeneratedTurn] = []
        for turn in range(max_user_turns):
            si = rng.randrange(len(seed_inputs))
            seed_text = seed_inputs[si]
            user_prompt = (
                f"Original user message:\n{seed_text!r}\n\n"
                f"Produce exactly one alternative user message for turn {turn + 1} of {max_user_turns}. "
                "Keep the same general intent but vary wording, length, or emphasis. "
                "Return strict JSON: {{\"messages\": [\"...\"]}} with a single string in the list."
            )
            parsed = await call_structured(
                model=self._model,
                system="You rewrite user messages for fuzz testing. Output JSON only.",
                user=user_prompt,
                response_model=_MutationsResponse,
                temperature=self._temperature,
                timeout_s=self._timeout_s,
            )
            if not parsed.messages or not str(parsed.messages[0]).strip():
                raise RuntimeError("llm_mutations: model returned empty message")
            msg = str(parsed.messages[0]).strip()
            out.append(
                GeneratedTurn(
                    message=msg,
                    label=f"mutation_of(seed[{si}])",
                    detail={"model": self._model, "seed_index": si},
                )
            )
        return out


def llm_mutations(
    *,
    model: str,
    temperature: float | None = None,
    timeout_s: float | None = None,
) -> Strategy:
    """Mutate ``seed_inputs`` via structured LLM calls (one mutation per generated turn)."""
    return _LLMMutationsStrategy(model=model, temperature=temperature, timeout_s=timeout_s)


__all__ = ["llm_mutations"]
