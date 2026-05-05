"""Parallel fuzz trials / shrink verification (process pool + driver)."""

from __future__ import annotations

import asyncio

from agent_spec_kit.fuzz.driver import RandomBatchFuzzerDriver
from agent_spec_kit.fuzz_config import ShrinkConfig
from agent_spec_kit.shrink import remove_user_turns
from agent_spec_kit.shrink_engine import shrink_user_turns


def test_random_batch_fuzzer_driver_gathers_trials() -> None:
    driver = RandomBatchFuzzerDriver()
    msgs = ({0: ("x",)}, {0: ("y",)}, {0: ("z",)})
    seen: list[int] = []

    async def submit_trial(ti: int, m: dict[int, tuple[str, ...]]) -> dict[str, object]:
        seen.append(ti)
        return {"trial_index": ti, "ok": True, "status": "passed", "fuzz": m}

    async def _run() -> None:
        out = await driver.run(
            submit_trial=submit_trial,
            trials_total=3,
            fuzz_messages_by_trial=msgs,
        )
        assert len(out) == 3

    asyncio.run(_run())
    assert set(seen) == {0, 1, 2}


def test_random_batch_fuzzer_driver_emits_trial_callbacks() -> None:
    driver = RandomBatchFuzzerDriver()
    msgs = ({0: ("x",)}, {0: ("y",)})
    starts: list[int] = []
    finishes: list[tuple[int, str]] = []

    async def submit_trial(ti: int, m: dict[int, tuple[str, ...]]) -> dict[str, object]:
        _ = m
        return {"trial_index": ti, "ok": True, "status": "passed"}

    async def _run() -> None:
        out = await driver.run(
            submit_trial=submit_trial,
            trials_total=2,
            fuzz_messages_by_trial=msgs,
            on_trial_started=lambda ti: starts.append(ti),
            on_trial_finished=lambda ti, o: finishes.append((ti, str(o.get("status")))),
        )
        assert len(out) == 2

    asyncio.run(_run())
    assert set(starts) == {0, 1}
    assert set(finishes) == {(0, "passed"), (1, "passed")}


def test_shrink_user_turns_verify_batch_remove_noise() -> None:
    async def verify_batch(cands: list[tuple[str, ...]]) -> list[bool]:
        return [c == ("keep",) for c in cands]

    async def _run() -> tuple[tuple[str, ...], int]:
        cfg = ShrinkConfig(passes=(remove_user_turns(),), confirm_runs=1, min_reproductions=1)
        return await shrink_user_turns(
            original=("noise", "keep"),
            shrinking=cfg,
            verify_batch=verify_batch,
        )

    shrunk, n = asyncio.run(_run())
    assert shrunk == ("keep",)
    assert n >= 1

