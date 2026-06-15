"""All frameworks must agree on golden traces via canonical_checks."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from shared.canonical_checks import CHECK_BY_ID
from shared.trace_io import load_trace


def test_golden_traces_pass_canonical_checks():
    for check_id, fn in sorted(CHECK_BY_ID.items()):
        trace = load_trace(check_id)
        assert fn(trace) is True, check_id
