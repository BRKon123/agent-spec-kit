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


def test_compare_uses_latest_per_scenario_across_runs(tmp_path: Path) -> None:
    store = LocalResultStore(StorageConfig(root=tmp_path / ".agent_spec_kit"))
    store.create_run(
        RunRecord(
            run_id="run_default_old",
            experiment_name="default",
            experiment_id="exp_default",
            started_at="2026-04-28T12:00:00+00:00",
            status="passed",
            command="agent-spec-kit run examples/langchain_arithmetic_llm_checks",
            notes=None,
            metadata={},
            git_commit=None,
            git_branch=None,
            git_dirty=None,
            python_version="3.12",
            package_version="0.1.0",
        )
    )
    store.create_run(
        RunRecord(
            run_id="run_trial_old",
            experiment_name="trial",
            experiment_id="exp_trial",
            started_at="2026-04-28T12:01:00+00:00",
            status="passed",
            command="agent-spec-kit run examples/langchain_arithmetic_llm_checks",
            notes=None,
            metadata={},
            git_commit=None,
            git_branch=None,
            git_dirty=None,
            python_version="3.12",
            package_version="0.1.0",
        )
    )
    store.create_run(
        RunRecord(
            run_id="run_default_new",
            experiment_name="default",
            experiment_id="exp_default",
            started_at="2026-04-28T12:02:00+00:00",
            status="failed",
            command="agent-spec-kit run examples/hardcoded_structured_output",
            notes=None,
            metadata={},
            git_commit=None,
            git_branch=None,
            git_dirty=None,
            python_version="3.12",
            package_version="0.1.0",
        )
    )

    store.save_scenario_result(
        ScenarioResultRecord(
            scenario_result_id="sr_default_arithmetic",
            run_id="run_default_old",
            scenario_name="test_arithmetic_with_llm_criteria_checks",
            scenario_module="m",
            scenario_file="f.py",
            scenario_key="test_arithmetic_with_llm_criteria_checks",
            parameter_key="default",
            parameters={},
            tags=(),
            status="passed",
            repeats_total=1,
            repeats_passed=1,
            repeats_failed=0,
            duration_ms=100,
            summary={},
        )
    )
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_default_arithmetic",
            scenario_result_id="sr_default_arithmetic",
            repeat_index=1,
            status="passed",
            started_at="2026-04-28T12:00:00+00:00",
            finished_at="2026-04-28T12:00:01+00:00",
            duration_ms=100,
            output_preview="ok",
            failure_kind=None,
            failure_message=None,
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )
    store.save_scenario_result(
        ScenarioResultRecord(
            scenario_result_id="sr_trial_arithmetic",
            run_id="run_trial_old",
            scenario_name="test_arithmetic_with_llm_criteria_checks",
            scenario_module="m",
            scenario_file="f.py",
            scenario_key="test_arithmetic_with_llm_criteria_checks",
            parameter_key="default",
            parameters={},
            tags=(),
            status="passed",
            repeats_total=1,
            repeats_passed=1,
            repeats_failed=0,
            duration_ms=120,
            summary={},
        )
    )
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_trial_arithmetic",
            scenario_result_id="sr_trial_arithmetic",
            repeat_index=1,
            status="passed",
            started_at="2026-04-28T12:01:00+00:00",
            finished_at="2026-04-28T12:01:01+00:00",
            duration_ms=120,
            output_preview="ok",
            failure_kind=None,
            failure_message=None,
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )
    store.save_scenario_result(
        ScenarioResultRecord(
            scenario_result_id="sr_default_hardcoded",
            run_id="run_default_new",
            scenario_name="test_hardcoded_structured_output_assertion",
            scenario_module="m",
            scenario_file="f.py",
            scenario_key="test_hardcoded_structured_output_assertion",
            parameter_key="default",
            parameters={},
            tags=(),
            status="failed",
            repeats_total=1,
            repeats_passed=0,
            repeats_failed=1,
            duration_ms=80,
            summary={},
        )
    )
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_default_hardcoded",
            scenario_result_id="sr_default_hardcoded",
            repeat_index=1,
            status="failed",
            started_at="2026-04-28T12:02:00+00:00",
            finished_at="2026-04-28T12:02:01+00:00",
            duration_ms=80,
            output_preview="bad",
            failure_kind="assert_tool_calls",
            failure_message="mismatch",
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )

    result = store.compare_experiments_most_recent(["exp_default", "exp_trial"])
    assert "excluded_fuzz_scenarios" in result
    assert result["excluded_fuzz_scenarios"] == []
    rows_by_key = {
        (row["scenario_key"], row["parameter_key"]): row for row in result["rows"]
    }
    assert ("test_arithmetic_with_llm_criteria_checks", "default") in rows_by_key
    assert ("test_hardcoded_structured_output_assertion", "default") in rows_by_key

    arithmetic_row = rows_by_key[("test_arithmetic_with_llm_criteria_checks", "default")]
    assert arithmetic_row["cells"]["exp_default"] is not None
    assert arithmetic_row["cells"]["exp_trial"] is not None

    hardcoded_row = rows_by_key[("test_hardcoded_structured_output_assertion", "default")]
    assert hardcoded_row["cells"]["exp_default"] is not None
    assert hardcoded_row["cells"]["exp_trial"] is None


def test_compare_excludes_fuzzed_scenario_rows(tmp_path: Path) -> None:
    store = LocalResultStore(StorageConfig(root=tmp_path / ".agent_spec_kit"))
    store.create_run(
        RunRecord(
            run_id="run_fuzz",
            experiment_name="default",
            experiment_id="exp_default",
            started_at="2026-04-28T12:00:00+00:00",
            status="passed",
            command="x",
            notes=None,
            metadata={},
            git_commit=None,
            git_branch=None,
            git_dirty=None,
            python_version="3.12",
            package_version="0.1.0",
        )
    )
    store.create_run(
        RunRecord(
            run_id="run_plain",
            experiment_name="trial",
            experiment_id="exp_trial",
            started_at="2026-04-28T12:01:00+00:00",
            status="passed",
            command="x",
            notes=None,
            metadata={},
            git_commit=None,
            git_branch=None,
            git_dirty=None,
            python_version="3.12",
            package_version="0.1.0",
        )
    )
    store.save_scenario_result(
        ScenarioResultRecord(
            scenario_result_id="sr_fuzz",
            run_id="run_fuzz",
            scenario_name="fuzzed",
            scenario_module="m",
            scenario_file="f.py",
            scenario_key="fuzzed",
            parameter_key="default",
            parameters={},
            tags=(),
            status="failed",
            repeats_total=1,
            repeats_passed=0,
            repeats_failed=1,
            duration_ms=10,
            summary={},
            fuzz_config_json='{"trials": 3}',
        )
    )
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_fuzz",
            scenario_result_id="sr_fuzz",
            repeat_index=1,
            status="failed",
            started_at="2026-04-28T12:00:00+00:00",
            finished_at="2026-04-28T12:00:01+00:00",
            duration_ms=10,
            output_preview="x",
            failure_kind="assert",
            failure_message="m",
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )
    store.save_scenario_result(
        ScenarioResultRecord(
            scenario_result_id="sr_plain",
            run_id="run_plain",
            scenario_name="plain",
            scenario_module="m",
            scenario_file="f.py",
            scenario_key="plain",
            parameter_key="default",
            parameters={},
            tags=(),
            status="passed",
            repeats_total=1,
            repeats_passed=1,
            repeats_failed=0,
            duration_ms=10,
            summary={},
            fuzz_config_json=None,
        )
    )
    store.save_repeat_result(
        RepeatResultRecord(
            repeat_result_id="rr_plain",
            scenario_result_id="sr_plain",
            repeat_index=1,
            status="passed",
            started_at="2026-04-28T12:01:00+00:00",
            finished_at="2026-04-28T12:01:01+00:00",
            duration_ms=10,
            output_preview="ok",
            failure_kind=None,
            failure_message=None,
            transcript_blob_path=None,
            assertions_blob_path=None,
            counterexample_blob_path=None,
            raw_error_blob_path=None,
        )
    )
    cmp = store.compare_experiments_most_recent(["exp_default", "exp_trial"])
    assert len(cmp["excluded_fuzz_scenarios"]) == 1
    assert cmp["excluded_fuzz_scenarios"][0]["scenario_key"] == "fuzzed"
    keys = {(r["scenario_key"], r["parameter_key"]) for r in cmp["rows"]}
    assert ("fuzzed", "default") not in keys
    assert ("plain", "default") in keys


def test_list_runs_pagination_and_count(tmp_path: Path) -> None:
    store = LocalResultStore(StorageConfig(root=tmp_path / ".agent_spec_kit"))
    for i in range(5):
        store.create_run(
            RunRecord(
                run_id=f"run_{i}",
                experiment_name="default",
                experiment_id="exp_default",
                started_at=f"2026-04-28T12:00:0{i}+00:00",
                status="passed" if i % 2 == 0 else "failed",
                command="agent-spec-kit run tests",
                notes=None,
                metadata={},
                git_commit=None,
                git_branch=None,
                git_dirty=None,
                python_version="3.12",
                package_version="0.1.0",
            )
        )
    assert store.count_runs() == 5
    assert store.count_runs(status="failed") == 2
    page0 = store.list_runs(limit=2, offset=0)
    page1 = store.list_runs(limit=2, offset=2)
    assert [r["run_id"] for r in page0] == ["run_4", "run_3"]
    assert [r["run_id"] for r in page1] == ["run_2", "run_1"]

