"""Fail traces must break canonical checks; golden traces must pass."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from catalog import SPECIMENS
from shared.canonical_checks import CHECK_BY_ID
from shared.fail_traces import fail_trace_for
from shared.trace_io import load_trace


def test_golden_traces_pass():
    for spec in SPECIMENS:
        assert CHECK_BY_ID[spec.check_id](load_trace(spec.check_id))


def test_fail_traces_break():
    for spec in SPECIMENS:
        cid = spec.check_id
        fail = fail_trace_for(cid)
        if cid == "C11":
            continue  # C11 fail uses oracle path without trace mutation
        assert not CHECK_BY_ID[cid](fail), cid
