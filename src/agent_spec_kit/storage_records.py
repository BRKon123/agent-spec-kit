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
    events_blob_path: str | None
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
        }

