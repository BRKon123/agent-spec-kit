"""Produce per-framework failure box text from artifacts + witnesses."""

from __future__ import annotations

from typing import Any

from scripts.diagnostic_quality_lib import FailureWitness, FRAMEWORKS

from diagnostic_comparison.implementations.run_checks import run_native_check as run_slot_check
from diagnostic_comparison.shared.artifact_io import load_artifact

_TRUNC = 4000


def _truncate(msg: str) -> str:
    msg = msg.strip()
    if len(msg) <= _TRUNC:
        return msg
    return msg[: _TRUNC - 3] + "..."


def format_agent_spec_kit(witness: FailureWitness) -> str:
    return _truncate(witness.panel_text or witness.headline)


def run_native_check(
    framework: str,
    witness: FailureWitness,
    artifact: dict[str, Any] | None,
) -> str:
    if artifact is None:
        return f"no artifact for {witness.family}|{witness.task}"
    return run_slot_check(framework, artifact, witness)


def run_framework(
    framework: str,
    witness: FailureWitness,
    *,
    artifact: dict[str, Any] | None = None,
) -> str:
    if framework == "agent_spec_kit":
        return format_agent_spec_kit(witness)
    if artifact is None:
        artifact = load_artifact(witness.family, witness.task)
    return run_native_check(framework, witness, artifact)


def framework_loc(framework: str, family: str = "", task: str = "") -> int:
    from diagnostic_comparison.implementations.run_checks import framework_loc as slot_loc

    if family and task:
        return slot_loc(framework, family, task)
    return 0


def collect_all_framework_messages(
    witness: FailureWitness,
    *,
    artifact: dict[str, Any] | None = None,
) -> dict[str, str]:
    if artifact is None:
        artifact = load_artifact(witness.family, witness.task)
    return {fw: run_framework(fw, witness, artifact=artifact) for fw in FRAMEWORKS}
