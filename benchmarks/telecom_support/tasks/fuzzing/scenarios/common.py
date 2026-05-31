"""Shared helpers for hand-authored fuzzing study scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import agent_spec_kit as ek
import yaml  # type: ignore[import-untyped]

from fuzz.mutations import mutation_operator_strategy
from store.store import TelcoStore
from tasks.user_simulation.scenarios.common import (
    Persona,
    build_user_prompt,
    build_user_simulator,
    cleanup_store,
    llm_model_cases,
    persona_cases,
    seeded_store,
)

BENCH = Path(__file__).resolve().parents[3]
CONFIG_PATH = BENCH / "tasks" / "fuzzing" / "study_config.yaml"
SEEDS_DIR = BENCH / "tasks" / "fuzzing" / "seeds"
FUZZ_TRIALS = 2


@dataclass(frozen=True)
class FuzzTrial:
    trial: int
    operator: str
    mutation_seed: int
    composition: tuple[str, ...] = ()


def load_fuzz_study_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_task_fuzz_plan(task_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    data = cfg or load_fuzz_study_config()
    plan = data["tasks"][task_id]
    return plan


def max_turns_for_segment(task_id: str, segment_index: int, cfg: dict[str, Any] | None = None) -> int:
    plan = load_task_fuzz_plan(task_id, cfg)
    for seg in plan["segments"]:
        if int(seg["index"]) == segment_index:
            return int(seg["max_user_turns"])
    raise KeyError(f"segment {segment_index} not configured for {task_id}")


def max_user_turns_by_segment(task_id: str, cfg: dict[str, Any] | None = None) -> list[int]:
    plan = load_task_fuzz_plan(task_id, cfg)
    return [int(s["max_user_turns"]) for s in sorted(plan["segments"], key=lambda x: int(x["index"]))]


def load_manual_seed_messages(task_id: str) -> list[str]:
    path = SEEDS_DIR / f"{task_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("messages") or [])


def segment_seed_messages(task_id: str, segment_index: int, cfg: dict[str, Any] | None = None) -> tuple[str, ...]:
    plan = load_task_fuzz_plan(task_id, cfg)
    all_msgs = load_manual_seed_messages(task_id)
    for seg in plan["segments"]:
        if int(seg["index"]) == segment_index:
            indices = [int(i) for i in seg.get("seed_turn_indices") or []]
            return tuple(all_msgs[i] for i in indices if 0 <= i < len(all_msgs))
    raise KeyError(f"segment {segment_index} not configured for {task_id}")


def fuzz_trial_cases(task_id: str, cfg: dict[str, Any] | None = None) -> tuple[ek.Case[FuzzTrial], ...]:
    plan = load_task_fuzz_plan(task_id, cfg)
    cases: list[ek.Case[FuzzTrial]] = []
    for row in plan["trials"]:
        comp = tuple(row.get("composition") or ())
        ft = FuzzTrial(
            trial=int(row["trial"]),
            operator=str(row["operator"]),
            mutation_seed=int(row["mutation_seed"]),
            composition=comp,
        )
        cases.append(
            ek.case(
                ft,
                id=f"op{ft.trial}_{ft.operator}{'_plus_' + '_'.join(comp) if comp else ''}",
            )
        )
    return tuple(cases)


def fuzz_config_for_segment(
    *,
    task_id: str,
    store: TelcoStore,
    fuzz_trial: FuzzTrial,
    segment_index: int,
    cfg: dict[str, Any] | None = None,
) -> ek.FuzzConfig:
    seeds = segment_seed_messages(task_id, segment_index, cfg)
    strategy = mutation_operator_strategy(
        operator_id=fuzz_trial.operator,
        seed_meta=dict(store.seed_meta),
        composition=fuzz_trial.composition,
    )
    return ek.FuzzConfig(
        strategy=strategy,
        seed_inputs=seeds,
        seed=fuzz_trial.mutation_seed,
    )


def store_fixture(task_id: str):
    @ek.fixture
    async def _store():
        store = seeded_store(task_id)
        try:
            yield store
        finally:
            cleanup_store(store)

    return _store


def agent_fixture(store_name: str):
    from agent_wrap import wrap_reference_agent

    @ek.fixture
    async def _agent(store):
        yield wrap_reference_agent(store)

    _agent.__name__ = f"task_agent_{store_name}"
    return _agent


def user_sim_fixture(task_id: str, intent: str, personas: tuple[Persona, ...], facts_fn):
    name = f"user_simulator_{task_id.lower()}"

    @ek.fixture
    @ek.parametrize("llm_model", llm_model_cases())
    @ek.parametrize("persona", persona_cases(personas))
    async def _sim(store, llm_model: str, persona: Persona):
        yield build_user_simulator(
            llm_model=llm_model,
            prompt=build_user_prompt(
                task_id=task_id,
                intent=intent,
                persona=persona,
                meta=store.seed_meta,
                scenario_facts=facts_fn(store),
            ),
        )

    _sim.__name__ = name
    return _sim
