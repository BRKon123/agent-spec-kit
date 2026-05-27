"""F10_T29 — braintrust: hand-written scenario check for diagnostic comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness

from diagnostic_comparison.shared.trace_helpers import tools_from_artifact_dict

def _check(artifact: dict[str, Any], witness: FailureWitness) -> None:
    tools = tools_from_artifact_dict(artifact)
    assert len(tools) >= 2, f"expected order_replacement_sim at index 1, got {len(tools)} tools"
    order = tools[1]
    assert order.get("name") == "order_replacement_sim"
    args = order.get("args") or {}
    assert "sim_type" not in args, (
        f"order_replacement_sim.args must not include sim_type; keys={list(args)!r}"
    )


def score(artifact: dict[str, Any], witness: FailureWitness) -> dict[str, Any]:
    try:
        _check(artifact, witness)
    except AssertionError as exc:
        return {"key": "f10_tool_sequence", "score": 0, "comment": str(exc)[:500]}
    return {"key": "f10_tool_sequence", "score": 1}

