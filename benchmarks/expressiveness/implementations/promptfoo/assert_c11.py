"""Promptfoo C11 — store oracle (no native DB assert in Promptfoo)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from specimens.messages import meta
from shared.store_sim import insert_ticket

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402


def get_assert(output: str, context: dict) -> bool:
    # CHECK_START
    _ = json.loads(output)
    base = Path(tempfile.mkdtemp(prefix="pf_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        insert_ticket(telco, line_id=meta()["line_id"])
        try:
            o.assert_ticket_exists(telco)
            return True
        except AssertionError:
            return False
    finally:
        shutil.rmtree(base, ignore_errors=True)
    # CHECK_END
