from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1] / "benchmarks" / "telecom_support"
sys.path.insert(0, str(BENCH / "scripts"))

from user_sim_extraction_study_lib import (  # noqa: E402
    count_user_turns,
    discover_extracted_scenario,
    extraction_config,
    extraction_summary,
    load_registry_for_extracted_rerun,
    signatures_match,
)
from agent_spec_kit.generative import FailureSignature


def test_extraction_config_points_at_extracted_sim() -> None:
    cfg = {"extraction": {"target_file": "../../regressions/extracted_sim/all_regressions.py"}}
    ext = extraction_config(cfg)
    assert "extracted_sim" in ext.target_file


def test_signatures_match() -> None:
    a = FailureSignature(check_kind="assert_tool_calls", path="$", assertion_id=None)
    b = FailureSignature(check_kind="assert_tool_calls", path="$", assertion_id=None)
    c = FailureSignature(check_kind="assert_output", path=None, assertion_id=None)
    assert signatures_match(a, b)
    assert not signatures_match(a, c)


def test_extraction_summary_counts() -> None:
    results = {
        "sim_records": [{"failure_signature": "x"}, {"failure_signature": None}],
        "candidates": [
            {"capture_status": "ok", "extraction": {"imports_ok": True, "collected": True, "reproduces_failure": True, "user_turns": 3, "extraction_status": "written"}},
            {"capture_status": "failed"},
        ],
    }
    s = extraction_summary(results)
    assert s["simulated_conversations"] == 2
    assert s["failing_conversations"] == 1
    assert s["capture_ok_eligible"] == 1
    assert s["regressions_extracted"] == 1
    assert s["same_failure_reproduction_rate_pct"] == 100.0


def test_count_user_turns() -> None:
    c = {"captured_per_step": {"0": ["a", "b"], "2": ["c"]}}
    assert count_user_turns(c) == 3


@pytest.mark.skipif(
    not (BENCH / "tasks/regressions/extracted_sim/all_regressions.py").exists()
    or "regression_REG_SIM_T20_0" not in (
        BENCH / "tasks/regressions/extracted_sim/all_regressions.py"
    ).read_text(encoding="utf-8"),
    reason="extracted regressions not generated yet",
)
def test_load_registry_discovers_extracted_regression() -> None:
    load_registry_for_extracted_rerun()
    sdef = discover_extracted_scenario("regression_REG_SIM_T20_0")
    assert sdef is not None
    assert sdef.name == "regression_REG_SIM_T20_0"
