"""Library utilities for telecom fuzzing study pipeline."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform
import re
import sys
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

import agent_spec_kit as ask
from agent_spec_kit.cli import (
    _aggregate_scenario_result,
    _save_fuzz_trials_for_repeat,
    _save_repeat_auxiliary,
    _write_repeat_blobs,
    collect_git_metadata,
)
from agent_spec_kit.discovery import collect_module_paths, import_paths
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.registries import ScenarioDef, iter_scenarios, reset_registries
from agent_spec_kit.result_store import LocalResultStore
from agent_spec_kit.runner import JobResult
from agent_spec_kit.scenario_core import tool_dicts_from_turn_data
from agent_spec_kit.storage_records import (
    RunRecord,
    ScenarioResultRecord,
    StorageConfig,
    parameter_key,
    scenario_key,
)
BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
SCENARIO_DIR = BENCH / "tasks" / "fuzzing" / "scenarios"
CONFIG_PATH = BENCH / "tasks" / "fuzzing" / "study_config.yaml"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from tasks.fuzzing.scenarios.common import load_fuzz_study_config, load_manual_seed_messages, max_user_turns_by_segment


def load_study_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return load_fuzz_study_config(path)


def discover_fuzz_study_scenarios() -> tuple[ScenarioDef, ...]:
    reset_registries()
    import_paths(collect_module_paths(SCENARIO_DIR))
    return iter_scenarios()


def _flatten_tool_names(tool_dict: dict[str, Any]) -> list[str]:
    name = str(tool_dict.get("name", "")).strip()
    children = tool_dict.get("children") or []
    if not children:
        return [name] if name else []
    child_parts: list[str] = []
    for ch in children:
        if isinstance(ch, dict):
            child_parts.extend(_flatten_tool_names(ch))
    if name:
        return [f"{name}[{' -> '.join(child_parts)}]"]
    return child_parts


def _extract_agent_tool_sequence(turn_results: tuple[Any, ...]) -> list[str]:
    seq: list[str] = []
    for turn in turn_results:
        if getattr(turn, "actor", None) != "agent":
            continue
        for td in tool_dicts_from_turn_data(turn):
            seq.extend(_flatten_tool_names(td))
    return seq


def _extract_agent_tool_set(turn_results: tuple[Any, ...]) -> list[str]:
    return sorted(set(_extract_agent_tool_sequence(turn_results)))


def _extract_agent_tool_bigrams(turn_results: tuple[Any, ...]) -> list[str]:
    seq = _extract_agent_tool_sequence(turn_results)
    return sorted({f"{seq[i]} -> {seq[i+1]}" for i in range(len(seq) - 1)})


def _parse_fuzz_trial_from_case_id(case_id: str) -> tuple[str | None, int | None]:
    m = re.search(r"op(\d+)_([^+]+)", case_id)
    if not m:
        return None, None
    return m.group(2).replace("_plus_", "+"), int(m.group(1))


def _user_messages_from_job(job: JobResult) -> list[str]:
    out: list[str] = []
    for turn in job.turn_results:
        if getattr(turn, "actor", None) == "user":
            text = getattr(turn, "text", None) or getattr(turn, "output", None)
            if text:
                out.append(str(text))
    return out


def record_from_fuzz_job(
    task_id: str,
    method: str,
    job: JobResult,
    *,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_study_config()
    turns = list(job.turn_results)
    user_turns = sum(1 for t in turns if getattr(t, "actor", None) == "user")
    agent_turns = sum(1 for t in turns if getattr(t, "actor", None) == "agent")
    tool_seq = _extract_agent_tool_sequence(job.turn_results)
    signature = " -> ".join(tool_seq) if tool_seq else "(no_tools)"
    failure_signature = None
    if not job.ok:
        detail = job.detail or job.failure_message or "failed"
        failure_signature = f"{job.failure_kind or job.status}:{detail}"

    seed = None
    mutation_operator = None
    mutation_seed = None
    framework_trials = int(cfg.get("framework_trials", 1))
    invalid_run_reason = None

    if method == "sim":
        m = re.search(r"seed(\d+)_", job.case_id)
        seed = int(m.group(1)) if m else None
    elif method == "fuzz":
        mutation_operator, mutation_seed = _parse_fuzz_trial_from_case_id(job.case_id)
        if user_turns == 0:
            invalid_run_reason = "invalid_fuzz"

    plan = cfg.get("tasks", {}).get(task_id, {})
    seed_passed = bool(plan.get("seed_passed_full_oracle", True))
    original_messages = load_manual_seed_messages(task_id)
    mutated_messages = _user_messages_from_job(job)

    baseline_type = "none"
    if task_id in {"T03", "T44"} and failure_signature:
        baseline_type = "existing_baseline_failure"
    elif failure_signature and method == "sim":
        baseline_type = "simulation_discovered_failure"
    elif failure_signature and method == "fuzz":
        baseline_type = "fuzz_discovered_failure"
    if method == "sim" and user_turns == 0:
        baseline_type = "invalid_simulation"

    per_step: list[tuple[str, ...]] = []
    if job.fuzz_trials:
        last = job.fuzz_trials[-1]
        per_step = [tuple(str(x) for x in seg) for seg in (last.get("per_step_user_turns") or ())]

    return {
        "task_id": task_id,
        "method": method,
        "seed": seed,
        "mutation_operator": mutation_operator,
        "mutation_seed": mutation_seed,
        "framework_trials": framework_trials if method == "fuzz" else 1,
        "trial_index": mutation_seed,
        "turn_count": len(turns),
        "agent_turn_count": agent_turns,
        "user_turn_count": user_turns,
        "final_status": job.status,
        "oracle_results": {"F": bool(job.ok)},
        "failure_signature": failure_signature,
        "tool_path_signature": signature,
        "tool_set": _extract_agent_tool_set(job.turn_results),
        "tool_bigram_set": _extract_agent_tool_bigrams(job.turn_results),
        "state_mutations": [],
        "baseline_failure_type": baseline_type,
        "scenario_name": job.scenario_name,
        "case_id": job.case_id,
        "duration_s": job.duration_s,
        "seed_source": "manual_script",
        "seed_passed_full_oracle": seed_passed,
        "original_user_messages": original_messages,
        "mutated_user_messages": mutated_messages,
        "max_user_turns_by_segment": max_user_turns_by_segment(task_id, cfg),
        "invalid_run_reason": invalid_run_reason,
        "per_step_user_turns": per_step,
        "calibration_steering": False,
    }


# Re-export UI logger from user simulation study
from user_simulation_lib import (  # noqa: E402
    UiStudyRunLogger,
    append_jsonl,
    write_transcript,
)

record_from_job = record_from_fuzz_job

__all__ = [
    "BENCH",
    "CONFIG_PATH",
    "UiStudyRunLogger",
    "append_jsonl",
    "discover_fuzz_study_scenarios",
    "load_study_config",
    "record_from_fuzz_job",
    "record_from_job",
    "write_transcript",
]
