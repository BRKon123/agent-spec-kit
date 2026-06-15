"""Tests for diagnostic panel parsing, deterministic metrics, and mocked LLM scoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from diagnostic_comparison.shared.artifact_io import load_artifact
from diagnostic_comparison.shared.run_framework import collect_all_framework_messages, run_framework
from scripts.diagnostic_quality_lib import (
    DIAGNOSTIC_SPECIFICITY_RUBRIC,
    DiagnosticColumns,
    FailureWitness,
    SpecificityScore,
    assess_columns_llm,
    assess_specificity_llm,
    cell_metrics,
    deterministic_metrics,
    metrics_from_failure_box,
    parse_failure_panels,
)

FIXTURE_LOG = Path(__file__).parent / "fixtures" / "sample_failure_panel.log"
RESULTS_PATH = BENCH / "tasks" / "fault_detection" / "fault_detection_results.json"


@pytest.fixture
def sample_panels():
    text = FIXTURE_LOG.read_text(encoding="utf-8")
    return parse_failure_panels(text)


def test_parse_failure_panel_scenario(sample_panels):
    w = sample_panels["test_f02_t29_full"]
    assert w.family == "F02"
    assert w.task == "T29"
    assert w.oracle == "F"
    assert w.check == "assert_tool_calls"
    assert "$[1]" in w.path
    assert "order_sim" in w.expected
    assert "LINE-WRONG" in w.actual
    assert "authenticate_customer" in (w.event_trace_text or w.panel_text)


def test_deterministic_metrics(sample_panels):
    m = deterministic_metrics(sample_panels["test_f02_t29_full"])
    assert m["failed_requirement_named"] is True
    assert m["trace_node_identified"] is True
    assert m["field_path_shown"] is True
    assert m["expected_vs_actual_shown"] is True
    assert m["nodes_to_inspect"] >= 1


def test_framework_messages_use_native_modules(sample_panels):
    w = sample_panels["test_f02_t29_full"]
    artifact = load_artifact("F02", "T29")
    if artifact is None:
        pytest.skip("run export_diagnostic_artifacts.py first")
    msgs = collect_all_framework_messages(w, artifact=artifact)
    assert "assert_tool_calls" in w.panel_text
    assert "sim_type" in msgs["pytest_plain"]
    assert msgs["promptfoo"] != "assertion returned False"
    assert "score" in msgs["langsmith"]
    assert msgs["pytest_plain"] != msgs["agent_spec_kit"]


def test_metrics_from_failure_box_pytest():
    box = "AssertionError: order_replacement_sim.args must not include sim_type"
    m = metrics_from_failure_box(box)
    assert m["failed_requirement_named"]
    assert m["expected_vs_actual_shown"]


def test_cell_metrics_agent_spec_kit_uses_witness(sample_panels):
    w = sample_panels["test_f02_t29_full"]
    m = cell_metrics(w.panel_text, w, framework="agent_spec_kit")
    assert m["field_path_shown"] is True


def test_assess_columns_llm_mock(sample_panels):
    import asyncio

    w = sample_panels["test_f02_t29_full"]

    async def mock_columns(**kwargs):
        return DiagnosticColumns(
            failed_requirement_named=True,
            trace_node_identified=True,
            field_path_shown=True,
            expected_vs_actual_shown=True,
            stable_signature=True,
        )

    scored = asyncio.run(
        assess_columns_llm(
            failure_box_text="sim_type must not appear in order_replacement_sim args",
            family="F02",
            task="T29",
            framework="pytest_plain",
            judge_fn=mock_columns,
        )
    )
    assert scored.failed_requirement_named is True


def test_assess_specificity_llm_mock(sample_panels):
    import asyncio

    w = sample_panels["test_f02_t29_full"]

    async def mock_judge(**kwargs):
        return SpecificityScore(specificity_grade="A", rationale="path and tools shown")

    scored = asyncio.run(
        assess_specificity_llm(
            failure_box_text=w.panel_text,
            diagnostic_target="wrong line in tool args",
            family="F02",
            task="T29",
            framework="agent_spec_kit",
            oracle="F",
            judge_fn=mock_judge,
        )
    )
    assert scored.specificity_grade == "A"
    assert scored.specificity_score == 4


def test_rubric_uses_letter_grades_aligned_with_expressiveness():
    assert "Grade" in DIAGNOSTIC_SPECIFICITY_RUBRIC
    assert "score: 0" in DIAGNOSTIC_SPECIFICITY_RUBRIC
    assert "AssertionError" in DIAGNOSTIC_SPECIFICITY_RUBRIC


def test_f_detected_count_in_committed_results():
    if not RESULTS_PATH.is_file():
        pytest.skip("no committed fault_detection_results.json")
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    n = sum(1 for r in data.values() if r.get("detected") and r.get("oracle") == "F")
    assert n >= 1
