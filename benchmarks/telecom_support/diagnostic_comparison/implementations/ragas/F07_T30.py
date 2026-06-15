"""F07_T30 — ragas: diagnostic slot via collections BaseMetric."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness

from diagnostic_comparison.shared.ragas_bridge import run_slot_check

_pytest = importlib.import_module("diagnostic_comparison.implementations.pytest_plain.F07_T30")


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> dict[str, Any]:
    return run_slot_check(_pytest.evaluate, artifact, witness, key="f07_t30")
