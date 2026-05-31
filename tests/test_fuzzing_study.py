"""Fuzzing study config, mutations, and scenario discovery."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BENCH = REPO / "benchmarks" / "telecom_support"
SCRIPTS = BENCH / "scripts"
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from agent_spec_kit.fixture_graph import scenario_case_runs
from fuzz.mutations import apply_operator, mutation_operator_strategy
from tasks.fuzzing.scenarios.common import (
    fuzz_trial_cases,
    load_fuzz_study_config,
    load_manual_seed_messages,
    max_turns_for_segment,
    segment_seed_messages,
)


def test_study_config_has_14_tasks():
    cfg = load_fuzz_study_config()
    assert len(cfg["primary_tasks"]) == 14
    for task in cfg["primary_tasks"]:
        plan = cfg["tasks"][task]
        assert len(plan["trials"]) == 5
        assert len(plan["segments"]) >= 2


def test_fuzz_trial_cases_count():
    cfg = load_fuzz_study_config()
    for task in cfg["primary_tasks"]:
        assert len(fuzz_trial_cases(task, cfg)) == 5


def test_apply_drop_required_fact():
    msgs = [
        "Account ACC-1, verification token VT-9, line LINE-1 — data is down.",
    ]
    out = apply_operator("drop_required_fact", list(msgs), seed_meta={}, rng=random.Random(0))
    assert "Account" not in out[0]


def test_mutation_strategy_eager_for_static_operator():
    strat = mutation_operator_strategy(operator_id="swap_entity", seed_meta={"line_id": "A", "line_id_2": "B"})
    assert strat.eager_generation is True


def test_mutation_strategy_lazy_for_dynamic_operator():
    strat = mutation_operator_strategy(
        operator_id="contradict_entity_later",
        seed_meta={"line_id": "LINE-A", "line_id_2": "LINE-B"},
    )
    assert strat.eager_generation is False


def test_manual_seeds_exist_for_all_tasks():
    cfg = load_fuzz_study_config()
    for task in cfg["primary_tasks"]:
        msgs = load_manual_seed_messages(task)
        assert isinstance(msgs, list)


def test_segment_seed_indices_in_range():
    cfg = load_fuzz_study_config()
    for task in cfg["primary_tasks"]:
        all_msgs = load_manual_seed_messages(task)
        for seg in cfg["tasks"][task]["segments"]:
            idx = int(seg["index"])
            got = segment_seed_messages(task, idx, cfg)
            for i in seg.get("seed_turn_indices") or []:
                assert 0 <= int(i) < len(all_msgs)
            assert max_turns_for_segment(task, idx, cfg) >= 1


@pytest.mark.parametrize("task_id", load_fuzz_study_config()["primary_tasks"])
def test_max_turns_match_config(task_id: str):
    cfg = load_fuzz_study_config()
    plan = cfg["tasks"][task_id]
    for seg in plan["segments"]:
        assert max_turns_for_segment(task_id, int(seg["index"]), cfg) == int(seg["max_user_turns"])


def test_fuzz_study_scenario_discovery_counts():
    from fuzzing_study_lib import discover_fuzz_study_scenarios

    scenarios = discover_fuzz_study_scenarios()
    manual = [s for s in scenarios if "method:manual" in s.tags]
    sim = [s for s in scenarios if "method:sim" in s.tags]
    fuzz = [s for s in scenarios if "method:fuzz" in s.tags]
    assert len(manual) == 14
    assert len(sim) == 14
    assert len(fuzz) == 14
    fuzz_cases = sum(len(scenario_case_runs(s)) for s in fuzz)
    sim_cases = sum(len(scenario_case_runs(s)) for s in sim)
    assert fuzz_cases == 70
    assert sim_cases == 70
