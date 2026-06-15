"""LLM-based semantic simplification for shrink passes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from pydantic import BaseModel, Field

from agent_spec_kit.fuzz_config import ShrinkPassSpec
from agent_spec_kit.judges.structured import call_structured


class _SimplifyResponse(BaseModel):
    variants: list[str] = Field(default_factory=list)


async def apply_llm_semantic_simplify(
    current: tuple[str, ...],
    spec: ShrinkPassSpec,
    *,
    verify_batch: Callable[[Sequence[tuple[str, ...]]], Awaitable[list[bool]]],
) -> tuple[tuple[str, ...], int]:
    """Shrink by replacing one message at a time with shorter LLM paraphrases."""
    model = str(spec.params.get("model", "")).strip()
    if not model:
        return current, 0
    n_cand = int(spec.params.get("candidates_per_message", 5))
    temperature = spec.params.get("temperature")
    timeout_s = spec.params.get("timeout_s")
    candidates_evaluated = 0
    changed = True
    while changed:
        changed = False
        for i, msg in enumerate(current):
            if not msg.strip():
                continue
            user_prompt = (
                f"Original user message:\n{msg!r}\n\n"
                f"Produce exactly {n_cand} shorter alternative messages that preserve "
                "the same intent, facts, and constraints. Each variant must be strictly "
                "shorter in character count than the original. Do not add new claims. "
                'Return strict JSON: {"variants": ["...", "..."]}.'
            )
            parsed = await call_structured(
                model=model,
                system=(
                    "You shorten user messages for test minimization. "
                    "Output JSON only with a variants list."
                ),
                user=user_prompt,
                response_model=_SimplifyResponse,
                temperature=temperature,
                timeout_s=timeout_s,
            )
            cands: list[tuple[str, ...]] = []
            for variant in parsed.variants:
                v = str(variant).strip()
                if not v or v == msg or len(v) >= len(msg):
                    continue
                cands.append(current[:i] + (v,) + current[i + 1 :])
            if not cands:
                continue
            results = await verify_batch(cands)
            candidates_evaluated += len(cands)
            wins = [c for c, ok in zip(cands, results, strict=True) if ok]
            if wins:
                best = min(wins, key=lambda c: (len(c), sum(len(x) for x in c)))
                if best != current:
                    current = best
                    changed = True
                    break
    return current, candidates_evaluated


__all__ = ["apply_llm_semantic_simplify"]
