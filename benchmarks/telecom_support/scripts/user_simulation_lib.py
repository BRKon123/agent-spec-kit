"""Library utilities for telecom user-simulation study pipeline."""

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
from agent_spec_kit.runner import JobResult, run_scenario_job
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


def _ui_run_id() -> str:
    ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    return f"run_{ts}_{uuid.uuid4().hex[:6]}"


def _experiment_id(name: str) -> str:
    return "exp_" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]  # noqa: S324


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class UiStudyRunLogger:
    """Persist study jobs to ``LocalResultStore`` for the agent-spec-kit results browser."""

    def __init__(
        self,
        *,
        experiment: str = "user-simulation-study",
        notes: str | None = None,
        study_run_id: str | None = None,
        command: str | None = None,
    ) -> None:
        self.store = LocalResultStore(StorageConfig(root=REPO / ".agent_spec_kit"))
        self.run_id = _ui_run_id()
        git_meta = collect_git_metadata()
        metadata: dict[str, str] = {}
        if study_run_id:
            metadata["study_run_id"] = study_run_id
        self.store.create_run(
            RunRecord(
                run_id=self.run_id,
                experiment_name=experiment,
                experiment_id=_experiment_id(experiment),
                started_at=_now_iso(),
                status="passed",
                command=command
                or "benchmarks/telecom_support/scripts/run_user_simulation_study.py",
                notes=notes,
                metadata=metadata,
                git_commit=git_meta["git_commit"],
                git_branch=git_meta["git_branch"],
                git_dirty=git_meta["git_dirty"],
                python_version=platform.python_version(),
                package_version=getattr(ask, "__version__", None),
            )
        )
        self._scenario_records: dict[tuple[str, int], ScenarioResultRecord] = {}
        self._scenario_repeats: dict[str, list[Any]] = {}

    def register(self, sdef: ScenarioDef, case_index: int) -> None:
        case = scenario_case_runs(sdef)[case_index]
        record = ScenarioResultRecord(
            scenario_result_id=f"{self.run_id}_{sdef.module}.{sdef.name}_{case_index:03d}",
            run_id=self.run_id,
            scenario_name=sdef.name,
            scenario_module=sdef.module,
            scenario_file=sdef.source,
            scenario_key=scenario_key(sdef.name, case),
            parameter_key=parameter_key(case),
            parameters={k: v.id for k, v in case.items()},
            tags=sdef.tags,
            status="skipped",
            repeats_total=sdef.repeats,
            repeats_passed=0,
            repeats_failed=0,
            duration_ms=None,
            summary={},
            fuzz_config_json=None,
        )
        key = (f"{sdef.module}.{sdef.name}", case_index)
        self._scenario_records[key] = record
        self._scenario_repeats[record.scenario_result_id] = []
        self.store.save_scenario_result(record)

    def persist_job(self, sdef: ScenarioDef, case_index: int, job: JobResult) -> None:
        key = (f"{sdef.module}.{sdef.name}", case_index)
        sr = self._scenario_records.get(key)
        if sr is None:
            return
        repeat_record, assertions = _write_repeat_blobs(
            store=self.store,
            run_id=self.run_id,
            scenario_result_id=sr.scenario_result_id,
            result=job,
        )
        self.store.save_repeat_result(repeat_record)
        _save_fuzz_trials_for_repeat(
            store=self.store,
            run_id=self.run_id,
            scenario_result_id=sr.scenario_result_id,
            result=job,
        )
        _save_repeat_auxiliary(
            store=self.store,
            run_id=self.run_id,
            scenario_result_id=sr.scenario_result_id,
            result=job,
        )
        for assertion in assertions:
            self.store.save_assertion_result(assertion)
        if job.fuzz_config_json and sr.fuzz_config_json is None:
            self._scenario_records[key] = dataclasses.replace(
                sr, fuzz_config_json=job.fuzz_config_json
            )
        self._scenario_repeats[sr.scenario_result_id].append(repeat_record)

    def finish(self) -> str:
        for sr in self._scenario_records.values():
            repeats = self._scenario_repeats[sr.scenario_result_id]
            self.store.save_scenario_result(_aggregate_scenario_result(sr, repeats))
        summary = self.store.compute_run_summary(self.run_id)
        self.store.finish_run(self.run_id, summary)
        return self.run_id
