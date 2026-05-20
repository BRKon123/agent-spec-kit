"""Smoke tests for Pydantic Evals-style evaluators (all 12)."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from implementations.pydantic_evals.evaluators import EVALUATORS


def test_all_evaluators_pass_on_golden_traces():
    for check_id, fn in EVALUATORS.items():
        assert fn(check_id) is True, check_id
