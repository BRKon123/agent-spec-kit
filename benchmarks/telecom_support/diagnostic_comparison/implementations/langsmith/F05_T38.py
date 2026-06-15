"""F05_T38 — langsmith: hand-written scenario check for diagnostic comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness

from diagnostic_comparison.shared.trace_helpers import find_tool, nested_child_names, tools_from_artifact_dict

def _check(artifact: dict[str, Any], witness: FailureWitness) -> None:
    tools = tools_from_artifact_dict(artifact)
    parent = find_tool(tools, "run_network_diagnostics_specialist")
    assert parent is not None, "missing run_network_diagnostics_specialist tool call"
    got = nested_child_names(parent)
    want = ["pull_network_events", "score_signal_anomaly"]
    assert got == want, f"expected nested tools {want!r}, got {got!r}"


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> dict[str, Any]:
    try:
        _check(artifact, witness)
    except AssertionError as exc:
        return {"key": "f05_tool_sequence", "score": 0, "comment": str(exc)[:500]}
    return {"key": "f05_tool_sequence", "score": 1}

