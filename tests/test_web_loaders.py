from __future__ import annotations

from pathlib import Path

from agent_spec_kit.result_store import write_json_blob
from agent_spec_kit.web import loaders


def test_build_fuzz_trial_detail_loads_counterexample_and_raw_error(tmp_path: Path) -> None:
    blob_dir = tmp_path / "blobs" / "run_1"
    blob_dir.mkdir(parents=True)
    transcript_path = write_json_blob(
        blob_dir / "rr_trial0001_transcript.json.gz",
        [{"actor": "user", "output": "hi", "events": []}],
    )
    cx_path = write_json_blob(
        blob_dir / "rr_trial0001_counterexample.json.gz",
        {
            "headline": "tool mismatch",
            "location": "step 1, turn 0",
            "path": "$[0].name",
            "expected_summary": "get_account",
            "actual_min": [{"name": "wrong"}],
            "notes": [],
            "check_kind": "assert_tool_calls",
            "location_detail": "after turn 0",
        },
    )
    raw_path = write_json_blob(
        blob_dir / "rr_trial0001_raw_error.json.gz",
        {"error": "boom"},
    )
    row = {
        "trial_id": "t1",
        "repeat_result_id": "rr_1",
        "trial_index": 1,
        "seed": 42,
        "status": "failed",
        "user_turns": ["hi"],
        "behaviour_labels": [],
        "behaviour_details": [],
        "summary_label": "mut",
        "failure_signature": None,
        "failure_kind": "assert_tool_calls",
        "failure_message": "tool mismatch",
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "duration_ms": 10,
        "transcript_blob_path": transcript_path,
        "counterexample_blob_path": cx_path,
        "raw_error_blob_path": raw_path,
        "scenario_name": "demo",
    }
    detail = loaders.build_fuzz_trial_detail(row)
    assert detail["transcript"] is not None
    assert detail["counterexample"]["headline"] == "tool mismatch"
    assert detail["raw_error"] == {"error": "boom"}
    assert detail["blob_errors"] == {}
    assert "transcript_blob_path" not in detail
    assert "counterexample_blob_path" not in detail


def test_save_fuzz_trial_persists_failure_blob_paths(tmp_path: Path) -> None:
    from agent_spec_kit.result_store import LocalResultStore
    from agent_spec_kit.storage_records import (
        RepeatResultRecord,
        RunRecord,
        ScenarioResultRecord,
        StorageConfig,
    )

    store = LocalResultStore(StorageConfig(root=tmp_path / ".agent_spec_kit"))
    store.create_run(
        RunRecord(
            run_id="run_1",
            experiment_name="default",
            experiment_id="exp_default",
            started_at="2026-01-01T00:00:00+00:00",
            status="passed",
            command=None,
            notes=None,
            metadata={},
            git_commit=None,
            git_branch=None,
            git_dirty=None,
            python_version=None,
            package_version=None,
        )
    )
    store.save_scenario_result(
        ScenarioResultRecord(
            scenario_result_id="sr_1",
            run_id="run_1",
            scenario_name="demo",
            scenario_module=None,
            scenario_file=None,
            scenario_key="demo",
            parameter_key="default",
            parameters={},
            tags=(),
            status="failed",
            repeats_total=1,
            repeats_passed=0,
            repeats_failed=1,
            duration_ms=1,
            summary={},
        )
    )
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_1",
            scenario_result_id="sr_1",
            repeat_index=1,
            status="failed",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at=None,
            duration_ms=1,
            output_preview=None,
            failure_kind=None,
            failure_message=None,
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )
    cx_path = write_json_blob(tmp_path / "cx.json.gz", {"headline": "x"})
    store.save_fuzz_trial(
        FuzzTrialRecord(
            trial_id="rr_1_fuzz0001",
            repeat_result_id="rr_1",
            trial_index=1,
            seed=1,
            status="failed",
            user_turns=("hi",),
            behaviour_labels=(),
            behaviour_details=(),
            summary_label="mut",
            failure_signature_json=None,
            failure_kind="assert_tool_calls",
            failure_message="x",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at=None,
            duration_ms=1,
            transcript_blob_path=None,
            counterexample_blob_path=cx_path,
            raw_error_blob_path=None,
        )
    )
    loaded = store.get_fuzz_trial("rr_1_fuzz0001")
    assert loaded is not None
    assert loaded["counterexample_blob_path"] == cx_path
