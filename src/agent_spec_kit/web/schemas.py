"""Pydantic response models for the web API.

Mirrors the dataclasses in :mod:`agent_spec_kit.storage_records` closely so
shapes don't drift, but uses ``BaseModel`` so FastAPI can serialize them
directly.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Status = Literal["passed", "failed", "error", "timeout", "skipped"]


class ProblemDetail(BaseModel):
    """RFC 7807 problem details. Returned for all API errors."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None


class ExperimentSummary(BaseModel):
    experiment_id: str
    name: str
    created_at: str | None = None
    run_count: int = 0
    last_run_at: str | None = None
    last_run_status: Status | None = None
    last_run_id: str | None = None


class RunListItem(BaseModel):
    run_id: str
    experiment_id: str
    experiment_name: str
    status: Status
    started_at: str
    finished_at: str | None = None
    scenario_passed: int = 0
    scenario_count: int = 0
    scenario_failed: int = 0
    repeat_pass_rate: float = 0.0
    mean_duration_ms: float = 0.0
    summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunListPage(BaseModel):
    """Paginated runs list for the results browser."""

    items: list[RunListItem]
    total: int
    limit: int
    offset: int


class RunDetail(BaseModel):
    run_id: str
    experiment_id: str | None = None
    experiment_name: str
    status: Status
    started_at: str
    finished_at: str | None = None
    command: str | None = None
    notes: str | None = None
    git_commit: str | None = None
    git_branch: str | None = None
    git_dirty: bool | None = None
    python_version: str | None = None
    package_version: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RepeatSummary(BaseModel):
    repeat_result_id: str
    repeat_index: int
    status: Status
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    output_preview: str | None = None
    failure_kind: str | None = None
    failure_message: str | None = None
    assertion_count: int = 0
    assertion_passed: int = 0


class ScenarioRow(BaseModel):
    scenario_result_id: str
    run_id: str
    scenario_name: str
    scenario_module: str | None = None
    scenario_file: str | None = None
    scenario_key: str
    parameter_key: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    status: Status
    repeats_total: int
    repeats_passed: int
    repeats_failed: int
    duration_ms: int | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    repeats: list[RepeatSummary] = Field(default_factory=list)


class AssertionRow(BaseModel):
    assertion_id: str
    assertion_type: str
    actor: str | None = None
    turn_index: int | None = None
    status: Status
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    counterexample_blob_path: str | None = None


class PhaseErrorRow(BaseModel):
    phase_error_id: str
    repeat_result_id: str
    phase: Literal["fuzz", "shrink", "extract"]
    sub_phase: str | None = None
    error_kind: str
    message: str
    traceback_blob_path: str | None = None
    occurred_at: str


class FuzzTrialSummary(BaseModel):
    trial_id: str
    repeat_result_id: str
    trial_index: int
    seed: int | None = None
    status: Status
    summary_label: str = ""
    failure_kind: str | None = None
    failure_message: str | None = None


class RepeatTrace(BaseModel):
    """Full trace payload for a single repeat: header + blob contents."""

    repeat_result_id: str
    scenario_result_id: str
    run_id: str
    scenario_name: str
    scenario_module: str | None = None
    scenario_key: str
    parameter_key: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    repeat_index: int
    status: Status
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    output_preview: str | None = None
    failure_kind: str | None = None
    failure_message: str | None = None
    assertions: list[AssertionRow] = Field(default_factory=list)
    transcript: Any | None = None
    counterexample: Any | None = None
    raw_error: Any | None = None
    blob_errors: dict[str, str] = Field(default_factory=dict)
    phase_errors: list[PhaseErrorRow] = Field(default_factory=list)
    fuzz_trials: list[FuzzTrialSummary] = Field(default_factory=list)


class CompareCellLatestRepeat(BaseModel):
    repeat_result_id: str
    repeat_index: int
    status: Status
    duration_ms: int | None = None
    failure_kind: str | None = None
    failure_message: str | None = None


class CompareCell(BaseModel):
    scenario_result_id: str
    run_id: str
    scenario_status: Status
    scenario_duration_ms: int | None = None
    repeats_passed: int
    repeats_failed: int
    repeats_total: int
    latest_repeat: CompareCellLatestRepeat | None = None


class CompareRow(BaseModel):
    scenario_key: str
    parameter_key: str
    scenario_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    cells: dict[str, CompareCell | None] = Field(default_factory=dict)


class CompareExperimentMeta(BaseModel):
    experiment_id: str
    name: str
    latest_run_id: str | None = None
    latest_run_started_at: str | None = None


class CompareResponse(BaseModel):
    experiments: list[CompareExperimentMeta]
    rows: list[CompareRow]
    excluded_fuzz_scenarios: list[dict[str, str]] = Field(default_factory=list)
