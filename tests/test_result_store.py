from __future__ import annotations

from pathlib import Path

from agent_spec_kit.result_store import LocalResultStore, write_json_blob
from agent_spec_kit.storage_records import (
    RepeatResultRecord,
    RunRecord,
    ScenarioResultRecord,
    StorageConfig,
)


def test_result_store_summary_and_blob_roundtrip(tmp_path: Path) -> None:
    store = LocalResultStore(StorageConfig(root=tmp_path / ".agent_spec_kit"))
    run = RunRecord(
        run_id="run_1",
        experiment_name="default",
        experiment_id="exp_default",
        started_at="2026-04-28T12:00:00+00:00",
        status="passed",
        command="agent-spec-kit run tests",
        notes=None,
        metadata={"model_family": "gpt"},
        git_commit=None,
        git_branch=None,
        git_dirty=None,
        python_version="3.12",
        package_version="0.1.0",
    )
    store.create_run(run)
    scenario = ScenarioResultRecord(
        scenario_result_id="sr_1",
        run_id="run_1",
        scenario_name="test_demo",
        scenario_module="m",
        scenario_file="f.py",
        scenario_key="test_demo[task=a]",
        parameter_key="task=a",
        parameters={"task": "a"},
        tags=("smoke",),
        status="failed",
        repeats_total=2,
        repeats_passed=1,
        repeats_failed=1,
        duration_ms=10,
        summary={},
    )
    store.save_scenario_result(scenario)
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_1",
            scenario_result_id="sr_1",
            repeat_index=1,
            status="passed",
            started_at="2026-04-28T12:00:00+00:00",
            finished_at="2026-04-28T12:00:01+00:00",
            duration_ms=100,
            output_preview="ok",
            failure_kind=None,
            failure_message=None,
            events_blob_path=None,
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_2",
            scenario_result_id="sr_1",
            repeat_index=2,
            status="failed",
            started_at="2026-04-28T12:00:02+00:00",
            finished_at="2026-04-28T12:00:03+00:00",
            duration_ms=220,
            output_preview="bad",
            failure_kind="assert_tool_calls",
            failure_message="mismatch",
            events_blob_path=None,
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )
    summary = store.compute_run_summary("run_1")
    assert summary.scenario_count == 1
    assert summary.repeat_count == 2
    assert summary.repeat_passed == 1
    assert summary.failure_kinds.get("assert_tool_calls") == 1

    blob_path = tmp_path / ".agent_spec_kit" / "blobs" / "run_1" / "demo.json.gz"
    written = write_json_blob(blob_path, {"hello": "world"})
    assert written.endswith("demo.json.gz")
    assert blob_path.exists()

