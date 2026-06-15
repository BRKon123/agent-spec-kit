"""F01_T44 — promptfoo: hand-written scenario check for diagnostic comparison."""
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
    assert tools, "expected tool calls in failing turn, got none"
    name = tools[0].get("name")
    assert name == "send_troubleshooting_step", (
        f"expected first tool send_troubleshooting_step, got {name!r}"
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

