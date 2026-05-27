"""F10_T43 — promptfoo: hand-written scenario check for diagnostic comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness


def _check(artifact: dict[str, Any], witness: FailureWitness) -> None:
    blob = str(artifact.get("witness_actual") or witness.actual or "")
    if "LLM criteria threshold failed" in blob:
        start = blob.find("LLM criteria threshold failed")
        raise AssertionError(blob[start : start + 400].strip())
    text = str(artifact.get("final_output") or "").lower()
    assert any(t in text for t in ("corrected", "correction", "wrong line")), (
        "expected acknowledgment that customer corrected which line needs the ticket"
    )


def get_assert(output: str, context: dict) -> bool | dict:
    artifact = json.loads(output)
    witness = FailureWitness(
        scenario=str(artifact.get("scenario", "")),
        family=str(artifact.get("family", "")),
        task=str(artifact.get("task", "")),
        oracle="F",
        actual=str(artifact.get("witness_actual", "")),
    )
    try:
        _check(artifact, witness)
    except AssertionError as exc:
        return {"pass": False, "score": 0, "reason": str(exc)[:500]}
    return True

