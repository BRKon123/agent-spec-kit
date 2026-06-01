"""Shrink passes for isolated generative failures."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Sequence

from agent_spec_kit.fuzz_config import ShrinkConfig, ShrinkPassSpec
from agent_spec_kit.shrink.llm_simplify import apply_llm_semantic_simplify


def _simplify_message(msg: str) -> tuple[str, ...]:
    """Deterministic variants (shortest first)."""
    m = msg.strip()
    out: list[str] = []
    if m:
        out.append(m)
        if len(m) > 1:
            out.append(m[:-1])
        if m.lower() != m:
            out.append(m.lower())
        if m.upper() != m:
            out.append(m.upper())
    return tuple(dict.fromkeys(out))


def _candidates_remove_one(turns: tuple[str, ...]) -> list[tuple[str, ...]]:
    if len(turns) <= 1:
        return []
    out: list[tuple[str, ...]] = []
    for i in range(len(turns)):
        out.append(turns[:i] + turns[i + 1 :])
    return out


def _candidates_simplify_messages(turns: tuple[str, ...]) -> list[tuple[str, ...]]:
    out: list[tuple[str, ...]] = []
    for i, msg in enumerate(turns):
        for variant in _simplify_message(msg):
            if variant == msg:
                continue
            cand = turns[:i] + (variant,) + turns[i + 1 :]
            out.append(cand)
    return out


def _take_budget(cands: list[tuple[str, ...]], budget: int | None) -> list[tuple[str, ...]]:
    if budget is None:
        return cands
    return cands[:budget]


async def _apply_pass(
    current: tuple[str, ...],
    spec: ShrinkPassSpec,
    *,
    verify_batch: Callable[[Sequence[tuple[str, ...]]], Awaitable[list[bool]]],
    budget: int | None = None,
) -> tuple[tuple[str, ...], int]:
    candidates_evaluated = 0
    if spec.kind == "remove_user_turns":
        changed = True
        while changed:
            if budget is not None and budget <= 0:
                break
            changed = False
            cands = _take_budget(_candidates_remove_one(current), budget)
            if not cands:
                break
            results = await verify_batch(cands)
            candidates_evaluated += len(cands)
            if budget is not None:
                budget -= len(cands)
            wins = [c for c, ok in zip(cands, results, strict=True) if ok]
            if wins:
                current = min(wins, key=lambda c: (len(c), sum(len(x) for x in c)))
                changed = True
        return current, candidates_evaluated

    if spec.kind == "simplify_user_messages":
        changed = True
        while changed:
            if budget is not None and budget <= 0:
                break
            changed = False
            cands = _take_budget(_candidates_simplify_messages(current), budget)
            if not cands:
                break
            results = await verify_batch(cands)
            candidates_evaluated += len(cands)
            if budget is not None:
                budget -= len(cands)
            wins = [c for c, ok in zip(cands, results, strict=True) if ok]
            if wins:
                current = min(wins, key=lambda c: (len(c), sum(len(x) for x in c)))
                changed = True
        return current, candidates_evaluated

    if spec.kind == "llm_semantic_simplify":
        if budget is not None and budget <= 0:
            return current, candidates_evaluated
        if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
            return current, candidates_evaluated
        cur, n = await apply_llm_semantic_simplify(current, spec, verify_batch=verify_batch)
        if budget is not None:
            n = min(n, budget)
        return cur, candidates_evaluated + n

    return current, candidates_evaluated


async def shrink_user_turns(
    *,
    original: tuple[str, ...],
    shrinking: ShrinkConfig,
    verify_batch: Callable[[Sequence[tuple[str, ...]]], Awaitable[list[bool]]],
) -> tuple[tuple[str, ...], int]:
    """Return ``(shrunk_turns, total_candidates_evaluated)``.

    ``verify_batch(candidates)`` returns a list of bools parallel to ``candidates``; ``True`` means the
    candidate still reproduces the target failure (same semantics as the old per-candidate ``verify``).
    """
    current = original
    total_candidates = 0
    budget = shrinking.max_attempts_per_shrink
    for spec in shrinking.passes:
        if budget is not None and budget <= 0:
            break
        cur, n = await _apply_pass(current, spec, verify_batch=verify_batch, budget=budget)
        total_candidates += n
        if budget is not None:
            budget -= n
        current = cur
    return current, total_candidates


__all__ = ["shrink_user_turns"]
