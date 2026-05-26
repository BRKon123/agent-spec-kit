"""Tests for diagnostic panel parsing, deterministic metrics, and mocked LLM scoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from diagnostic_comparison.shared.run_framework import (
    collect_all_framework_messages,
    format_pytest_plain,
    run_framework,
)
from scripts.diagnostic_quality_lib import (
    DIAGNOSTIC_SPECIFICITY_RUBRIC,
    FailureWitness,
    SpecificityScore,
    assess_specificity_llm,
    deterministic_metrics,
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


def test_framework_messages_differ(sample_panels):
    w = sample_panels["test_f02_t29_full"]
    msgs = collect_all_framework_messages(w)
    assert "assert_tool_calls" in w.panel_text
    assert "AssertionError" in msgs["pytest_plain"]
    assert msgs["promptfoo"] == "assertion returned False"
    assert "score" in msgs["langsmith"]


def test_assess_specificity_llm_mock(sample_panels):
    import asyncio

    w = sample_panels["test_f02_t29_full"]

    async def mock_judge(**kwargs):
        return SpecificityScore(specificity_score=4, rationale="path and tools shown")

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
    assert scored.specificity_score == 4


def test_rubric_scores_named_eval_keys_above_bare_assertion():
    assert "f10_output_rubric" in DIAGNOSTIC_SPECIFICITY_RUBRIC
    assert "assertion returned False" in DIAGNOSTIC_SPECIFICITY_RUBRIC
    assert "Score 2" in DIAGNOSTIC_SPECIFICITY_RUBRIC


def test_f_detected_count_in_committed_results():
    if not RESULTS_PATH.is_file():
        pytest.skip("no committed fault_detection_results.json")
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    n = sum(1 for r in data.values() if r.get("detected") and r.get("oracle") == "F")
    assert n >= 1
