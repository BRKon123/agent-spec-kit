"""Stable storage-facing record dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from agent_spec_kit.param_cases import Case

Status = Literal["passed", "failed", "error", "timeout", "skipped"]


@dataclass(frozen=True, slots=True)
class StorageConfig:
    root: Path = Path(".agent_spec_kit")
    sqlite_path: Path | None = None


class ResultStore(Protocol):
    def create_run(self, run: "RunRecord") -> None: ...

    def save_scenario_result(self, result: "ScenarioResultRecord") -> None: ...

    def save_repeat_result(self, result: "RepeatResultRecord") -> None: ...

    def save_assertion_result(self, result: "AssertionResultRecord") -> None: ...

    def save_fuzz_trial(self, result: "FuzzTrialRecord") -> None: ...

    def save_shrink_result(self, result: "ShrinkResultRecord") -> None: ...

    def save_regression(self, result: "RegressionExtractionRecord") -> None: ...

    def save_phase_error(self, result: "PhaseErrorRecord") -> None: ...

    def compute_run_summary(self, run_id: str) -> "RunSummary": ...

    def finish_run(self, run_id: str, summary: "RunSummary") -> None: ...


def scenario_key(name: str, parameters: dict[str, Case[Any]]) -> str:
    if not parameters:
        return name
    parts = [f"{param_name}={case.id}" for param_name, case in sorted(parameters.items())]
    return f"{name}[{','.join(parts)}]"


def parameter_key(parameters: dict[str, Case[Any]]) -> str:
    if not parameters:
        return "default"
    return "+".join(f"{param_name}={case.id}" for param_name, case in sorted(parameters.items()))


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    experiment_name: str
    experiment_id: str
    started_at: str
    status: Status
    command: str
    notes: str | None
    metadata: dict[str, Any]
    git_commit: str | None
    git_branch: str | None
    git_dirty: bool | None
    python_version: str
    package_version: str | None


@dataclass(frozen=True, slots=True)
class ScenarioResultRecord:
    scenario_result_id: str
    run_id: str
    scenario_name: str
    scenario_module: str | None
    scenario_file: str | None
    scenario_key: str
    parameter_key: str
    parameters: dict[str, Any]
    tags: tuple[str, ...]
    status: Status
    repeats_total: int
    repeats_passed: int
    repeats_failed: int
    duration_ms: int | None
    summary: dict[str, Any] = field(default_factory=dict)
    fuzz_config_json: str | None = None


@dataclass(frozen=True, slots=True)
class FuzzTrialRecord:
    trial_id: str
    repeat_result_id: str
    trial_index: int
    seed: int | None
    status: Status
    user_turns: tuple[str, ...]
    behaviour_labels: tuple[str, ...]
    behaviour_details: tuple[dict[str, Any], ...]
    summary_label: str
    failure_signature_json: str | None
    failure_kind: str | None
    failure_message: str | None
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    transcript_blob_path: str | None
    counterexample_blob_path: str | None = None
    raw_error_blob_path: str | None = None
    #: Per original step index: user-side turns (empty for non-generative steps).
    per_step_user_turns: tuple[tuple[str, ...], ...] | None = None


@dataclass(frozen=True, slots=True)
class ShrinkResultRecord:
    shrink_id: str
    repeat_result_id: str
    source_trial_id: str | None
    status: Status
    passes_applied: tuple[str, ...]
    original_user_turns: tuple[str, ...]
    shrunk_user_turns: tuple[str, ...]
    candidates_evaluated: int
    duration_ms: int | None
    started_at: str
    finished_at: str | None
    generative_step_index: int | None = None
    step_kind: str | None = None


@dataclass(frozen=True, slots=True)
class RegressionExtractionRecord:
    regression_id: str
    run_id: str
    scenario_result_id: str
    shrink_id: str | None
    source_scenario_key: str
    target_file: str
    function_name: str
    fingerprint: str
    duplicate_policy: str
    status: str
    written_at: str | None


@dataclass(frozen=True, slots=True)
class PhaseErrorRecord:
    phase_error_id: str
    repeat_result_id: str
    phase: Literal["fuzz", "shrink", "extract"]
    sub_phase: str | None
    error_kind: str
    message: str
    traceback_blob_path: str | None
    occurred_at: str


@dataclass(frozen=True, slots=True)
class RepeatResultRecord:
    repeat_result_id: str
    scenario_result_id: str
    repeat_index: int
    status: Status
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    output_preview: str | None
    failure_kind: str | None
    failure_message: str | None
    transcript_blob_path: str | None
    assertions_blob_path: str | None
    counterexample_blob_path: str | None
    raw_error_blob_path: str | None


@dataclass(frozen=True, slots=True)
class AssertionResultRecord:
    assertion_id: str
    repeat_result_id: str
    assertion_type: str
    actor: str | None
    turn_index: int | None
    status: Status
    message: str | None
    details: dict[str, Any]
    counterexample_blob_path: str | None


@dataclass(frozen=True, slots=True)
class RunSummary:
    status: Status
    scenario_count: int
    scenario_passed: int
    scenario_failed: int
    scenario_errored: int
    scenario_timeout: int
    repeat_count: int
    repeat_passed: int
    repeat_failed: int
    repeat_pass_rate: float
    scenario_pass_rate: float
    flaky_scenarios: int
    mean_duration_ms: float
    p50_duration_ms: int
    p95_duration_ms: int
    failure_kinds: dict[str, int]
    tag_breakdown: dict[str, int]
    parameter_breakdown: dict[str, dict[str, Any]]
    fuzz_trials_total: int = 0
    fuzz_trials_failed: int = 0
    regressions_written: int = 0
    regressions_skipped: int = 0
    phase_errors_total: int = 0

    def as_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scenario_count": self.scenario_count,
            "scenario_passed": self.scenario_passed,
            "scenario_failed": self.scenario_failed,
            "scenario_errored": self.scenario_errored,
            "scenario_timeout": self.scenario_timeout,
            "repeat_count": self.repeat_count,
            "repeat_passed": self.repeat_passed,
            "repeat_failed": self.repeat_failed,
            "repeat_pass_rate": self.repeat_pass_rate,
            "scenario_pass_rate": self.scenario_pass_rate,
            "flaky_scenarios": self.flaky_scenarios,
            "mean_duration_ms": self.mean_duration_ms,
            "p50_duration_ms": self.p50_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "failure_kinds": self.failure_kinds,
            "tag_breakdown": self.tag_breakdown,
            "parameter_breakdown": self.parameter_breakdown,
            "fuzz_trials_total": self.fuzz_trials_total,
            "fuzz_trials_failed": self.fuzz_trials_failed,
            "regressions_written": self.regressions_written,
            "regressions_skipped": self.regressions_skipped,
            "phase_errors_total": self.phase_errors_total,
        }

