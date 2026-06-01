from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1] / "benchmarks" / "telecom_support"
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

sys.path.insert(0, str(BENCH / "scripts"))
from user_sim_shrink_study_lib import (  # noqa: E402
    candidate_id,
    estimate_tokens,
    estimate_turn_tokens,
    flat_turns,
    split_user_turns_across_segments,
    stratified_pick,
)
from agent_spec_kit.scenario_core import _SimulateStep


def test_estimate_tokens() -> None:
    assert estimate_tokens("one two three") == 3


def test_split_single_segment() -> None:
    steps = [(3, _SimulateStep(5, None, "agent", None, None))]
    out = split_user_turns_across_segments(["a", "b"], steps)
    assert out == {3: ("a", "b")}


def test_split_multi_segment() -> None:
    steps = [
        (1, _SimulateStep(3, None, "agent", "user", "open")),
        (5, _SimulateStep(5, None, "agent", None, None)),
    ]
    msgs = ["open", "u2", "u3", "u4"]
    out = split_user_turns_across_segments(msgs, steps)
    assert sum(len(v) for v in out.values()) == len(msgs)
    assert flat_turns(out) == tuple(msgs)


def test_stratified_pick_spreads_buckets() -> None:
    items = [
        {"task": "T1", "k": "a"},
        {"task": "T1", "k": "b"},
        {"task": "T2", "k": "a"},
    ]
    picked = stratified_pick(items, 2, key_fn=lambda x: x["task"])
    assert len(picked) == 2
    tasks = {p["task"] for p in picked}
    assert len(tasks) == 2


def test_candidate_id_format() -> None:
    assert candidate_id("T43", 0) == "SIM-T43-0"
