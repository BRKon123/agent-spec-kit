"""Smoke tests for LangSmith-style evaluators."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from implementations.langsmith.evaluators import EVALUATORS, run_evaluator


def test_all_evaluators_pass_on_golden_traces():
    for check_id in sorted(EVALUATORS):
        result = run_evaluator(check_id)
        assert result["score"] == 1, check_id
