"""F10_T43 — pytest_plain: hand-written scenario check for diagnostic comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> None:
    blob = str(artifact.get("witness_actual") or witness.actual or "")
    if "LLM criteria threshold failed" in blob:
        start = blob.find("LLM criteria threshold failed")
        raise AssertionError(blob[start : start + 400].strip())
    text = str(artifact.get("final_output") or "").lower()
    assert any(t in text for t in ("corrected", "correction", "wrong line")), (
        "expected acknowledgment that customer corrected which line needs the ticket"
    )


