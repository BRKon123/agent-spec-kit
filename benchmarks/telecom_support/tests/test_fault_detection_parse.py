"""Unit tests for fault-detection log parsing and eligibility."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.fault_detection_lib import (  # noqa: E402
    enrich_detection,
    parse_baseline_eligibility,
    parse_fault_detection_log,
)


SAMPLE_BASELINE = """
PASS test_t03_trace [1/1]
FAIL test_t03_full [1/1]
PASS test_t44_output [1/1]
"""

SAMPLE_FAULT = """
PASS test_f01_t03_full [1/1]
FAIL test_f01_t03_trace [1/1]
FAIL test_f01_t44_trace [1/1]
"""


def test_parse_baseline_eligibility():
    elig = parse_baseline_eligibility(SAMPLE_BASELINE)
    assert elig["T03"]["T"] is True
    assert elig["T03"]["F"] is False
    assert elig["T44"]["O"] is True


def test_parse_fault_detection_log():
    raw = parse_fault_detection_log(SAMPLE_FAULT)
    assert raw["F01|T03|F"]["passed"] is True
    assert raw["F01|T03|T"]["passed"] is False
    assert raw["F01|T44|T"]["fault"] == "F01"


def test_enrich_detection():
    raw = parse_fault_detection_log(SAMPLE_FAULT)
    eligibility = {"T03": {"T": True, "F": True}, "T44": {"T": True}}
    enriched = enrich_detection(raw, eligibility)
    assert enriched["F01|T03|T"]["eligible"] is True
    assert enriched["F01|T03|T"]["detected"] is True
    assert enriched["F01|T03|F"]["eligible"] is True
    assert enriched["F01|T03|F"]["detected"] is False


def test_committed_eligibility_json_valid():
    path = BENCH / "tasks" / "fault_detection" / "eligibility.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "T01" in data
    assert set(data["T01"].keys()) == {"O", "S", "T", "F"}
