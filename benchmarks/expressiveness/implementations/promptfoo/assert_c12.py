"""Promptfoo assertion for C12 — inlined check logic."""

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
    turns = trace.get("turns") or []
    if not turns:
        return False
    last = turns[-1]
    names = tool_names(walk_root_tools(last))
    if not ordered_subsequence(
        ["authenticate_customer", "create_support_ticket"], names, allow_extras=True
    ):
        return False
    mmeta = meta()
    base = Path(tempfile.mkdtemp(prefix="canon_c12_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        insert_ticket(telco, line_id=mmeta["line_id"], ticket_id="INC-9046")
        try:
            o.assert_ticket_for_line(telco, mmeta["line_id"])
            return True
        except AssertionError:
            return False
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END
