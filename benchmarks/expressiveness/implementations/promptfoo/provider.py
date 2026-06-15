"""Promptfoo custom provider: frozen trace JSON + trajectory spans for native asserts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from implementations.promptfoo.trace_spans import frozen_trace_to_promptfoo_trace
from shared.trace_io import load_trace


def call_api(prompt: str, options: dict, context: dict) -> dict:
    vars_ = context.get("vars") or {}
    check_id = str(vars_.get("check_id") or prompt or "C01")
    trace = load_trace(check_id)
    return {
        "output": json.dumps(trace),
        "trace": frozen_trace_to_promptfoo_trace(trace, check_id),
    }
