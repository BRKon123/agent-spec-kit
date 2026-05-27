"""F07_T43 — langsmith: hand-written scenario check for diagnostic comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness

from diagnostic_comparison.shared.trace_helpers import first_forbidden_index, tools_from_artifact_dict

def _check(artifact: dict[str, Any], witness: FailureWitness) -> None:
    tools = tools_from_artifact_dict(artifact)
    idx = first_forbidden_index(tools, "create_support_ticket")
    assert idx is None, f"forbidden tool create_support_ticket at index {idx}"


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> dict[str, Any]:
    try:
        _check(artifact, witness)
    except AssertionError as exc:
        return {"key": "f07_forbidden_tools", "score": 0, "comment": str(exc)[:500]}
    return {"key": "f07_forbidden_tools", "score": 1}

