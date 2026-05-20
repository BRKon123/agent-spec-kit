"""Smoke tests for Braintrust-style scorers (all 12)."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from shared.trace_io import load_trace
from implementations.braintrust.scorers import SCORERS


def test_all_scorers_pass_on_golden_traces():
    for check_id, fn in SCORERS.items():
        trace = load_trace(check_id)
        result = fn(trace)
        assert result["score"] == 1, check_id
