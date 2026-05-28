"""Library utilities for telecom user-simulation study pipeline."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from agent_spec_kit.discovery import collect_module_paths, import_paths
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.registries import ScenarioDef, iter_scenarios, reset_registries
from agent_spec_kit.runner import JobResult, run_scenario_job
from agent_spec_kit.scenario_core import tool_dicts_from_turn_data

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
SCENARIO_DIR = BENCH / "tasks" / "user_simulation" / "scenarios"
MANUAL_DIR = BENCH / "tasks" / "manual"
CONFIG_PATH = BENCH / "tasks" / "user_simulation" / "study_config.yaml"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))


def load_study_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def discover_user_sim_scenarios() -> tuple[ScenarioDef, ...]:
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
    out = sorted(set(_extract_agent_tool_sequence(turn_results)))
    return out


def _extract_agent_tool_bigrams(turn_results: tuple[Any, ...]) -> list[str]:
    seq = _extract_agent_tool_sequence(turn_results)
    return sorted({f"{seq[i]} -> {seq[i+1]}" for i in range(len(seq) - 1)})


def _seed_from_case_id(case_id: str) -> int | None:
    m = re.search(r"seed(\d+)_", case_id)
    if not m:
        return None
    return int(m.group(1))


def record_from_job(task_id: str, method: str, job: JobResult) -> dict[str, Any]:
    turns = list(job.turn_results)
    user_turns = sum(1 for t in turns if getattr(t, "actor", None) == "user")
    agent_turns = sum(1 for t in turns if getattr(t, "actor", None) == "agent")
    tool_seq = _extract_agent_tool_sequence(job.turn_results)
    signature = " -> ".join(tool_seq) if tool_seq else "(no_tools)"
    failure_signature = None
    if not job.ok:
        detail = job.detail or job.failure_message or "failed"
        failure_signature = f"{job.failure_kind or job.status}:{detail}"
    seed = _seed_from_case_id(job.case_id) if method == "sim" else None
    baseline_type = "none"
    if task_id in {"T03", "T44"} and failure_signature:
        baseline_type = "existing_baseline_failure"
    elif failure_signature and method == "sim":
        baseline_type = "simulation_discovered_failure"
    if method == "sim" and user_turns == 0:
        baseline_type = "invalid_simulation"
    return {
        "task_id": task_id,
        "method": method,
        "seed": seed,
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
    }


async def run_scenario_cases(scenario_def: ScenarioDef) -> list[JobResult]:
    cases = scenario_case_runs(scenario_def)
    out: list[JobResult] = []
    for idx in range(len(cases)):
        out.append(
            await run_scenario_job(
                scenario_def,
                case_index=idx,
                repeat_index=1,
                repeat_total=1,
            )
        )
    return out


def write_transcript(path: Path, job: JobResult) -> None:
    payload = {
        "scenario_name": job.scenario_name,
        "case_id": job.case_id,
        "status": job.status,
        "ok": job.ok,
        "turn_results": [asdict(t) for t in job.turn_results],
        "detail": job.detail,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
