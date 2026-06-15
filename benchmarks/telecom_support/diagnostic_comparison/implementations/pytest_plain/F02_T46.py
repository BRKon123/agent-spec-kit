"""F02_T46 — pytest_plain: hand-written scenario check for diagnostic comparison."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness
from diagnostic_comparison.shared.trace_helpers import tools_from_artifact_dict


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> None:
    """send_troubleshooting_step must not carry a structured step arg."""
    tools = tools_from_artifact_dict(artifact)
    if len(tools) < 2:
        blob = str(artifact.get("witness_actual") or witness.actual or "")
        if "unexpected key 'step'" in blob or 'unexpected key \'step\'' in blob:
            raise AssertionError(
                "send_troubleshooting_step.args must not include step key"
            )
        raise AssertionError(
            f"expected send_troubleshooting_step at index 1, got {len(tools)} tools"
        )
    step_tool = tools[1]
    assert step_tool.get("name") == "send_troubleshooting_step"
    args = step_tool.get("args") or {}
    assert "step" not in args, (
        f"send_troubleshooting_step.args must not include step key; keys={list(args)!r}"
    )
