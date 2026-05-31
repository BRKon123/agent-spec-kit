"""Tests for fuzz segment context and lazy generation hooks."""

from __future__ import annotations

import random

import pytest

from agent_spec_kit.fuzz_context import build_fuzz_segment_context, strategy_eager_generation
from agent_spec_kit.fuzz_types import FuzzSegmentContext, GeneratedTurn
from agent_spec_kit.run import ConversationTurn


class _LazyStrategy:
    eager_generation = False
    seen: list[FuzzSegmentContext | None] = []

    async def generate(
        self,
        *,
        rng: random.Random,
        max_user_turns: int,
        seed_inputs: tuple[str, ...],
        context: FuzzSegmentContext | None = None,
    ):
        _LazyStrategy.seen.append(context)
        if context and context.prior_agent_messages:
            return (GeneratedTurn(message="follow-up correction", label="lazy"),)
        return (GeneratedTurn(message=seed_inputs[0] if seed_inputs else "hi", label="seed"),)


class _EagerStrategy:
    eager_generation = True

    async def generate(
        self,
        *,
        rng: random.Random,
        max_user_turns: int,
        seed_inputs: tuple[str, ...],
        context: FuzzSegmentContext | None = None,
    ):
        _ = context
        return (GeneratedTurn(message="eager", label="eager"),)


def test_build_fuzz_segment_context_collects_transcript():
    turns = (
        ConversationTurn(actor="user", output="hello"),
        ConversationTurn(
            actor="agent",
            output="checking",
            events=[{"type": "tool", "name": "authenticate_customer"}],
        ),
    )
    ctx = build_fuzz_segment_context(turns, segment_index=1)
    assert ctx.prior_user_messages == ("hello",)
    assert ctx.prior_agent_messages == ("checking",)
    assert ctx.segment_index == 1
    assert ctx.prior_agent_messages == ("checking",)


def test_strategy_eager_generation_flags():
    assert strategy_eager_generation(_EagerStrategy()) is True
    assert strategy_eager_generation(_LazyStrategy()) is False


def test_lazy_strategy_uses_prior_agent_text():
    import asyncio

    _LazyStrategy.seen.clear()
    strat = _LazyStrategy()
    turns = (
        ConversationTurn(actor="user", output="wrong line"),
        ConversationTurn(actor="agent", output="noted wrong line"),
    )
    ctx = build_fuzz_segment_context(turns, segment_index=1)
    out = asyncio.run(
        strat.generate(
            rng=random.Random(0),
            max_user_turns=3,
            seed_inputs=("seed",),
            context=ctx,
        )
    )
    assert out[0].message == "follow-up correction"
