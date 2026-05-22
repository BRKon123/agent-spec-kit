"""Shared helpers for fault-detection eligibility, log parsing, and matrix loading."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

BENCH = Path(__file__).resolve().parents[1]
FAULT_DIR = BENCH / "tasks" / "fault_detection"
MATRIX_PATH = BENCH / "tasks" / "fault_matrix.yaml"
ELIGIBILITY_PATH = FAULT_DIR / "eligibility.json"
RESULTS_PATH = FAULT_DIR / "fault_detection_results.json"
META_PATH = FAULT_DIR / "fault_detection_run_meta.json"
DEFAULT_BASELINE_LOG = BENCH / "tasks" / "calibration_logs" / "baseline_T01_T50.log"
DEFAULT_FAULT_LOG = FAULT_DIR / "fault_detection_primary.log"

ORACLE_FROM_KIND = {"full": "F", "trace": "T", "state": "S", "output": "O"}
ORACLE_TO_KIND = {v: k for k, v in ORACLE_FROM_KIND.items()}

_FAULT_SCENARIO_RE = re.compile(
    r"^(PASS|FAIL)\s+test_f(\d+)_t(\d+)_(full|trace|state|output)\s+\[(\d+)/(\d+)\]",
    re.IGNORECASE,
)


def load_fault_matrix(path: Path | None = None) -> dict[str, Any]:
    p = path or MATRIX_PATH
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def matrix_file_hash(path: Path | None = None) -> str:
    p = path or MATRIX_PATH
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def variant_for_pair(matrix: dict[str, Any], family: str, task: str) -> str:
    fam = matrix["families"][family]
    if "task_variants" in fam:
        key = fam["task_variants"].get(task, "default")
        if "variants" in fam:
            return fam["variants"][key]
        return fam["variants"][key]
    return fam["variant"]


def primary_pairs(matrix: dict[str, Any] | None = None) -> list[tuple[str, str, str]]:
    """Return (family_id, task_id, variant_id) for primary matrix."""
    matrix = matrix or load_fault_matrix()
    out: list[tuple[str, str, str]] = []
    for family, spec in matrix["families"].items():
        for task in spec["primary"]:
            out.append((family, task, variant_for_pair(matrix, family, task)))
    return out


def expected_scenario_names(
    matrix: dict[str, Any] | None = None,
    *,
    primary_only: bool = True,
) -> list[str]:
    matrix = matrix or load_fault_matrix()
    names: list[str] = []
    pairs = primary_pairs(matrix) if primary_only else []
    if not primary_only:
        raise NotImplementedError("expansion matrix not wired yet")
    for family, task, _variant in pairs:
        fnum = family[1:]
        tnum = task[1:]
        for kind in ("full", "trace", "state", "output"):
            names.append(f"test_f{fnum}_t{tnum}_{kind}")
    return names


def parse_baseline_eligibility(log_text: str) -> dict[str, dict[str, bool]]:
    """Parse reference baseline log into per-task oracle pass flags."""
    sys_path_insert = str(BENCH)
    import sys

    if sys_path_insert not in sys.path:
        sys.path.insert(0, sys_path_insert)
    from scripts.run_calibration import parse_results

    parsed = parse_results(log_text)
    eligibility: dict[str, dict[str, bool]] = {}
    for (tid, oracle), runs in parsed.items():
        if not runs:
            continue
        eligibility.setdefault(tid, {})[oracle] = bool(runs[0])
    return eligibility


def parse_fault_detection_log(log_text: str) -> dict[str, dict[str, Any]]:
    """Parse fault-detection scenario PASS/FAIL lines."""
    records: dict[str, dict[str, Any]] = {}
    for line in log_text.splitlines():
        m = _FAULT_SCENARIO_RE.match(line.strip())
        if not m:
            continue
        status, fnum, tnum, kind, rep, total = m.groups()
        if int(total) != 1 or int(rep) != 1:
            continue
        family = f"F{int(fnum):02d}"
        task = f"T{int(tnum):02d}"
        oracle = ORACLE_FROM_KIND[kind.lower()]
        key = f"{family}|{task}|{oracle}"
        scenario = f"test_f{fnum}_t{tnum}_{kind.lower()}"
        records[key] = {
            "fault": family,
            "task": task,
            "oracle": oracle,
            "scenario": scenario,
            "passed": status.upper() == "PASS",
            "run_status": status.lower(),
        }
    return records


def enrich_detection(
    results: dict[str, dict[str, Any]],
    eligibility: dict[str, dict[str, bool]],
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for key, rec in results.items():
        task = rec["task"]
        oracle = rec["oracle"]
        eligible = eligibility.get(task, {}).get(oracle, False)
        passed = rec["passed"]
        enriched[key] = {
            **rec,
            "eligible": eligible,
            "detected": eligible and not passed,
        }
    return enriched
