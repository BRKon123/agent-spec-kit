#!/usr/bin/env python3
"""Scaffold deepeval/ragas diagnostic slot modules from pytest_plain ports."""

from __future__ import annotations

from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
DIAG = BENCH / "diagnostic_comparison" / "implementations"
PYTEST_DIR = DIAG / "pytest_plain"

DEEPEVAL_TEMPLATE = '''"""{slot} — deepeval: diagnostic slot via BaseMetric SlotAssertMetric."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[3]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness

from diagnostic_comparison.shared.deepeval_bridge import run_slot_check

_pytest = importlib.import_module("diagnostic_comparison.implementations.pytest_plain.{module}")


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> dict[str, Any]:
    return run_slot_check(_pytest.evaluate, artifact, witness, key="{key}")
'''

RAGAS_TEMPLATE = '''"""{slot} — ragas: diagnostic slot via collections BaseMetric."""
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

_pytest = importlib.import_module("diagnostic_comparison.implementations.pytest_plain.{module}")


def evaluate(artifact: dict[str, Any], witness: FailureWitness) -> dict[str, Any]:
    return run_slot_check(_pytest.evaluate, artifact, witness, key="{key}")
'''


def _slot_key(stem: str) -> str:
    family, task = stem.split("_", 1)
    return f"{family.lower()}_{task.lower()}"


def main() -> None:
    for framework, template in (("deepeval", DEEPEVAL_TEMPLATE), ("ragas", RAGAS_TEMPLATE)):
        out_dir = DIAG / framework
        out_dir.mkdir(parents=True, exist_ok=True)
        init = out_dir / "__init__.py"
        if not init.is_file():
            init.write_text('"""Native diagnostic ports."""\n', encoding="utf-8")

        for src in sorted(PYTEST_DIR.glob("F*.py")):
            stem = src.stem
            key = _slot_key(stem)
            content = template.format(slot=stem, module=stem, key=key)
            (out_dir / f"{stem}.py").write_text(content, encoding="utf-8")
            print(f"wrote {framework}/{stem}.py")


if __name__ == "__main__":
    main()
