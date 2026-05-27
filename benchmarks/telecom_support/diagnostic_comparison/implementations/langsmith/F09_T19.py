"""F09_T19 — pytest_plain: hand-written scenario check for diagnostic comparison."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness
from diagnostic_comparison.shared.store_from_artifact import with_store
from tasks.specs import oracles as o


def _run_check(artifact: dict[str, Any], witness: FailureWitness) -> None:
    """State oracle replay for F09_T19 (idiomatic pytest assert)."""
    def _oracle(store):
        o.assert_ticket_exists(store)
    try:
        with_store(artifact, _oracle)
    except AssertionError:
        raise
    msg = (witness.state_message or witness.expected or "state check failed").strip()
    if msg.startswith("assert_that failed:"):
        msg = msg.split("assert_that failed:", 1)[1].strip()
    raise AssertionError(msg)


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> dict[str, Any]:
    try:
        _run_check(artifact, witness)
    except AssertionError as exc:
        return {"key": "f09_state_oracle", "score": 0, "comment": str(exc)[:500]}
    return {"key": "f09_state_oracle", "score": 1}

