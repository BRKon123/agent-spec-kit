"""Fuzzer drivers: own trial emission strategy per (scenario, case, repeat) group."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class FuzzerDriver(Protocol):
    """Owns how trials are scheduled for one repeat of a generative scenario."""

    async def run(
        self,
        *,
        submit_trial: Callable[[int, dict[int, tuple[str, ...]]], Awaitable[Any]],
        trials_total: int,
        fuzz_messages_by_trial: Sequence[dict[int, tuple[str, ...]]],
        on_trial_started: Callable[[int], None] | None = None,
        on_trial_finished: Callable[[int, Any], None] | None = None,
    ) -> Sequence[Any]:
        """Call ``submit_trial(trial_index, fuzz_messages_by_step_index)`` and collect outcomes."""


class RandomBatchFuzzerDriver:
    """Submit all trials in parallel (via ``asyncio.gather`` on ``submit_trial``)."""

    async def run(
        self,
        *,
        submit_trial: Callable[[int, dict[int, tuple[str, ...]]], Awaitable[Any]],
        trials_total: int,
        fuzz_messages_by_trial: Sequence[dict[int, tuple[str, ...]]],
        on_trial_started: Callable[[int], None] | None = None,
        on_trial_finished: Callable[[int, Any], None] | None = None,
    ) -> list[Any]:
        import asyncio

        async def run_one(ti: int) -> tuple[int, Any]:
            if on_trial_started is not None:
                on_trial_started(ti)
            out = await submit_trial(ti, dict(fuzz_messages_by_trial[ti]))
            if on_trial_finished is not None:
                on_trial_finished(ti, out)
            return ti, out

        tasks = [asyncio.create_task(run_one(t)) for t in range(trials_total)]
        out_by_trial: dict[int, Any] = {}
        for task in asyncio.as_completed(tasks):
            ti, out = await task
            out_by_trial[ti] = out
        return [out_by_trial[t] for t in range(trials_total)]


def pick_fuzzer_driver(_probe: Any) -> FuzzerDriver:
    """Select a driver from probe metadata (extension point for coverage-guided fuzzers)."""
    return RandomBatchFuzzerDriver()


__all__ = ["FuzzerDriver", "RandomBatchFuzzerDriver", "pick_fuzzer_driver"]
