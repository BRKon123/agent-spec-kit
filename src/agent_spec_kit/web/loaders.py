"""Helpers that bridge :class:`LocalResultStore` rows + blob files into API DTOs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_spec_kit.result_store import LocalResultStore, read_json_blob
from agent_spec_kit.scenario_core import tool_dicts_from_transcript


def _counterexample_actual_min_needs_repair(actual_min: Any, *, check_kind: str | None) -> bool:
    if check_kind != "assert_tool_calls":
        return False
    if isinstance(actual_min, list):
        return False
    if not isinstance(actual_min, str):
        return True
    stripped = actual_min.rstrip()
    return stripped.endswith("...") or stripped.startswith(("[", "{"))


def repair_counterexample_for_display(
    counterexample: Any,
    transcript: Any,
    *,
    turn_index: int | None = None,
) -> Any:
    """
    Upgrade legacy counterexamples whose ``actual_min`` was stored as a truncated string.

    Older builds set ``actual_min`` to a capped JSON string; rehydrate from the transcript
    blob when possible so the UI can show the full tool-call list without re-running.
    """
    if not isinstance(counterexample, dict):
        return counterexample
    check_kind = counterexample.get("check_kind")
    actual_min = counterexample.get("actual_min")
    if not _counterexample_actual_min_needs_repair(actual_min, check_kind=check_kind):
        return counterexample
    tools = tool_dicts_from_transcript(transcript, turn_index=turn_index)
    if not tools:
        return counterexample
    repaired = dict(counterexample)
    repaired["actual_min"] = tools
    return repaired


def load_blob_safely(path: str | None) -> tuple[Any | None, str | None]:
    """Return ``(payload, error_message)``. Missing path returns ``(None, None)``.

    Errors are caught and returned as strings so the API can include them in
    ``blob_errors`` without failing the whole trace endpoint.
    """
    if path is None:
        return None, None
    p = Path(path)
    if not p.exists():
        return None, f"blob file missing: {path}"
    try:
        return read_json_blob(p), None
    except Exception as e:  # noqa: BLE001 - surface any blob error to the API
        return None, f"{type(e).__name__}: {e}"


def _turn_index_from_counterexample(counterexample: Any) -> int | None:
    if not isinstance(counterexample, dict):
        return None
    location = counterexample.get("location")
    if not isinstance(location, str):
        return None
    for part in location.split(","):
        part = part.strip()
        if part.startswith("turn "):
            try:
                return int(part.removeprefix("turn ").strip())
            except ValueError:
                return None
    return None


def build_fuzz_trial_detail(row: dict[str, Any]) -> dict[str, Any]:
    """Build a fuzz-trial detail dict with transcript and failure blobs loaded."""
    blob_errors: dict[str, str] = {}

    transcript, err = load_blob_safely(row.get("transcript_blob_path"))
    if err:
        blob_errors["transcript"] = err
    counterexample, err = load_blob_safely(row.get("counterexample_blob_path"))
    if err:
        blob_errors["counterexample"] = err
    raw_error, err = load_blob_safely(row.get("raw_error_blob_path"))
    if err:
        blob_errors["raw_error"] = err

    counterexample = repair_counterexample_for_display(
        counterexample,
        transcript,
        turn_index=_turn_index_from_counterexample(counterexample),
    )

    out = {k: v for k, v in row.items() if not k.endswith("_blob_path")}
    out["transcript"] = transcript
    out["counterexample"] = counterexample
    out["raw_error"] = raw_error
    out["blob_errors"] = blob_errors
    return out


def build_repeat_trace(
    store: LocalResultStore, repeat_result_id: str
) -> dict[str, Any] | None:
    """Build a full :class:`RepeatTrace`-shaped dict, loading all available blobs."""
    rec = store.get_repeat(repeat_result_id)
    if rec is None:
        return None

    blob_errors: dict[str, str] = {}

    transcript, err = load_blob_safely(rec["transcript_blob_path"])
    if err:
        blob_errors["transcript"] = err
    counterexample, err = load_blob_safely(rec["counterexample_blob_path"])
    if err:
        blob_errors["counterexample"] = err
    raw_error, err = load_blob_safely(rec["raw_error_blob_path"])
    if err:
        blob_errors["raw_error"] = err

    failed_turn_index: int | None = None
    for assertion in rec.get("assertions") or []:
        if assertion.get("status") != "passed" and assertion.get("turn_index") is not None:
            failed_turn_index = int(assertion["turn_index"])
            break
    counterexample = repair_counterexample_for_display(
        counterexample,
        transcript,
        turn_index=failed_turn_index,
    )

    phase_errors = store.list_phase_errors(repeat_result_id)
    fuzz_rows = store.list_fuzz_trials(repeat_result_id)
    fuzz_trials = [
        {
            "trial_id": ft["trial_id"],
            "repeat_result_id": ft["repeat_result_id"],
            "trial_index": ft["trial_index"],
            "seed": ft.get("seed"),
            "status": ft["status"],
            "summary_label": ft.get("summary_label", ""),
            "failure_kind": ft.get("failure_kind"),
            "failure_message": ft.get("failure_message"),
        }
        for ft in fuzz_rows
    ]

    return {
        "repeat_result_id": rec["repeat_result_id"],
        "scenario_result_id": rec["scenario_result_id"],
        "run_id": rec["run_id"],
        "scenario_name": rec["scenario_name"],
        "scenario_module": rec["scenario_module"],
        "scenario_key": rec["scenario_key"],
        "parameter_key": rec["parameter_key"],
        "parameters": rec["parameters"],
        "tags": rec["tags"],
        "repeat_index": rec["repeat_index"],
        "status": rec["status"],
        "started_at": rec["started_at"],
        "finished_at": rec["finished_at"],
        "duration_ms": rec["duration_ms"],
        "output_preview": rec["output_preview"],
        "failure_kind": rec["failure_kind"],
        "failure_message": rec["failure_message"],
        "assertions": rec["assertions"],
        "transcript": transcript,
        "counterexample": counterexample,
        "raw_error": raw_error,
        "blob_errors": blob_errors,
        "phase_errors": phase_errors,
        "fuzz_trials": fuzz_trials,
    }
