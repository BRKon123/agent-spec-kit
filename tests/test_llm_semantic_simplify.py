from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import pytest

from agent_spec_kit.fuzz_config import ShrinkPassSpec
from agent_spec_kit.shrink.llm_simplify import apply_llm_semantic_simplify


def test_llm_semantic_simplify_picks_verified_shorter_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_call_structured(**kwargs: Any) -> Any:
        from agent_spec_kit.shrink.llm_simplify import _SimplifyResponse

        _ = kwargs
        return _SimplifyResponse(variants=["hi", "hey"])

    monkeypatch.setattr(
        "agent_spec_kit.shrink.llm_simplify.call_structured",
        fake_call_structured,
    )

    async def verify_batch(cands: Sequence[tuple[str, ...]]) -> list[bool]:
        return [c == ("hi",) for c in cands]

    spec = ShrinkPassSpec(
        kind="llm_semantic_simplify",
        params={"model": "openai:gpt-5-nano", "candidates_per_message": 2},
    )
    shrunk, n = asyncio.run(
        apply_llm_semantic_simplify(
            ("hello world",),
            spec,
            verify_batch=verify_batch,
        )
    )
    assert shrunk == ("hi",)
    assert n >= 1


def test_llm_semantic_simplify_skips_without_model() -> None:
    async def verify_batch(cands: Sequence[tuple[str, ...]]) -> list[bool]:
        return [True] * len(cands)

    spec = ShrinkPassSpec(kind="llm_semantic_simplify", params={})
    shrunk, n = asyncio.run(
        apply_llm_semantic_simplify(
            ("hello",),
            spec,
            verify_batch=verify_batch,
        )
    )
    assert shrunk == ("hello",)
    assert n == 0
