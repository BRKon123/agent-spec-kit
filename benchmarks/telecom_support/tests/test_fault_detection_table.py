"""Table generator uses JSON math only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.generate_fault_detection_table import generate_table  # noqa: E402
from scripts.fault_detection_lib import load_fault_matrix  # noqa: E402


def test_generate_table_detection_rate():
    eligibility = {
        "T03": {"O": True, "T": True, "S": True, "F": True},
        "T37": {"O": True, "T": False, "S": False, "F": False},
    }
    results = {
        "F01|T03|O": {"fault": "F01", "task": "T03", "oracle": "O", "passed": True, "detected": False},
        "F01|T03|T": {"fault": "F01", "task": "T03", "oracle": "T", "passed": False, "detected": True},
        "F01|T03|S": {"fault": "F01", "task": "T03", "oracle": "S", "passed": False, "detected": True},
        "F01|T03|F": {"fault": "F01", "task": "T03", "oracle": "F", "passed": False, "detected": True},
        "F01|T37|O": {"fault": "F01", "task": "T37", "oracle": "O", "passed": False, "detected": True},
    }
    matrix = {
        "families": {
            "F01": {
                "variant": "fault_premature_escalate",
                "primary": ["T03", "T37"],
            }
        },
        "diagnostics": {"F01": ["T03"]},
    }
    md = generate_table(results, eligibility, {"matrix_hash": "test"}, matrix)
    assert "1/2 (50%)" in md  # F01/O: T03 missed, T37 detected
    assert "detected" in md
    assert "F01" in md
