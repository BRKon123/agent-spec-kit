"""Promptfoo custom provider: returns frozen trace output as model response."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from shared.trace_io import load_trace


def call_api(prompt: str, options: dict, context: dict) -> dict:
    check_id = os.environ.get("EXPR_CHECK_ID", "C05")
    trace = load_trace(check_id)
    return {
        "output": json.dumps(trace),
    }
