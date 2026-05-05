"""Helpers that bridge :class:`LocalResultStore` rows + blob files into API DTOs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_spec_kit.result_store import LocalResultStore, read_json_blob


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
