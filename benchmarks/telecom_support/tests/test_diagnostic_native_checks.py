"""Tests for hand-written per-scenario framework diagnostic modules."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from diagnostic_comparison.implementations.run_checks import run_native_check
from diagnostic_comparison.shared.artifact_io import slot_artifact_path
from diagnostic_comparison.shared.run_framework import run_framework
from scripts.diagnostic_quality_lib import FailureWitness, parse_failure_panels

LOG = BENCH / "tasks" / "fault_detection" / "fault_detection_primary.log"


@pytest.fixture
def f02_t29_witness():
    text = LOG.read_text(encoding="utf-8", errors="replace") if LOG.is_file() else ""
    panels = parse_failure_panels(text)
    w = panels.get("test_f02_t29_full")
    if w is None:
        pytest.skip("no test_f02_t29_full panel in fault_detection_primary.log")
    return w


@pytest.fixture
def f02_t29_artifact(f02_t29_witness):
    path = slot_artifact_path("F02", "T29")
    if not path.is_file():
        pytest.skip("run export_diagnostic_artifacts.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_native_check_imports_slot_module(f02_t29_artifact, f02_t29_witness):
    msg = run_native_check("pytest_plain", f02_t29_artifact, f02_t29_witness)
    assert msg != "unexpected pass"
    assert "sim_type" in msg


def test_langsmith_returns_score_dict(f02_t29_artifact, f02_t29_witness):
    msg = run_framework("langsmith", f02_t29_witness, artifact=f02_t29_artifact)
    assert "score" in msg
    assert "'score': 0" in msg or '"score": 0' in msg


def test_promptfoo_not_bare_false(f02_t29_artifact, f02_t29_witness):
    msg = run_framework("promptfoo", f02_t29_witness, artifact=f02_t29_artifact)
    assert msg != "assertion returned False"
    assert "reason" in msg


def test_each_framework_invokes_own_module(f02_t29_artifact, f02_t29_witness):
    for fw in ("pytest_plain", "langsmith", "pydantic_evals", "promptfoo", "braintrust"):
        mod_path = f"diagnostic_comparison.implementations.{fw}.F02_T29"
        with patch.object(importlib, "import_module", wraps=importlib.import_module) as imp:
            run_native_check(fw, f02_t29_artifact, f02_t29_witness)
            imp.assert_called()
            assert imp.call_args[0][0] == mod_path


def test_no_run_core_check_in_run_checks_source():
    src = (BENCH / "diagnostic_comparison/implementations/run_checks.py").read_text()
    assert "run_core_check" not in src
    assert "check_dispatch" not in src
