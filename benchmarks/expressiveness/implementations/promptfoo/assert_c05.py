"""Promptfoo assertion for C05 — inlined check logic."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from specimens.messages import meta
from shared.store_sim import insert_ticket
from shared.trace_helpers import (
    any_forbidden_present,
    find_tool,
    nested_children,
    ordered_subsequence,
    tool_names,
    unordered_set,
    walk_root_tools,
)

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402

import json

def get_assert(output: str, context: dict) -> bool | float | dict:
    trace = json.loads(output)
    # CHECK_START
    names = tool_names(walk_root_tools(trace))
    return ordered_subsequence(
        ["authenticate_customer", "get_outage_status"], names, allow_extras=True
    )
    # CHECK_END
