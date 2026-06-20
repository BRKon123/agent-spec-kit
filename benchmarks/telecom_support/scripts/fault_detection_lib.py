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
DEFAULT_BASELINE_LOG = BENCH / "tasks" / "baseline_logs" / "baseline_T01_T50.log"
DEFAULT_FAULT_LOG = FAULT_DIR / "fault_detection_primary.log"
DEFAULT_PAIRED_LOG = FAULT_DIR / "paired.log"
DEFAULT_PAIRED_JSON = FAULT_DIR / "paired.json"
DEFAULT_TRACE_DIR = FAULT_DIR / "paired_trace"

ORACLE_FROM_KIND = {"full": "F", "trace": "T", "state": "S", "output": "O"}
ORACLE_TO_KIND = {v: k for k, v in ORACLE_FROM_KIND.items()}

_FAULT_SCENARIO_RE = re.compile(
    r"^(PASS|FAIL)\s+test_f(\d+)_t(\d+)_(full|trace|state|output)\s+\[(\d+)/(\d+)\]",
    re.IGNORECASE,
)

_REFERENCE_SCENARIO_RE = re.compile(
    r"^(PASS|FAIL)\s+test_t(\d+)_(full|trace|state|output)\s+\[(\d+)/(\d+)\]",
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
    eligibility: dict[str, dict[str, bool]] = {}
    for rec in parse_reference_log(log_text).values():
        eligibility.setdefault(rec["task"], {})[rec["oracle"]] = bool(rec["passed"])
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


def load_eligibility(path: Path | None = None) -> dict[str, dict[str, bool]]:
    p = path or ELIGIBILITY_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def parse_reference_log(log_text: str) -> dict[str, dict[str, Any]]:
    """Parse reference manual scenario PASS/FAIL lines keyed by task|oracle."""
    records: dict[str, dict[str, Any]] = {}
    for line in log_text.splitlines():
        m = _REFERENCE_SCENARIO_RE.match(line.strip())
        if not m:
            continue
        status, tnum, kind, rep, total = m.groups()
        if int(total) != 1 or int(rep) != 1:
            continue
        task = f"T{int(tnum):02d}"
        oracle = ORACLE_FROM_KIND[kind.lower()]
        key = f"{task}|{oracle}"
        records[key] = {
            "task": task,
            "oracle": oracle,
            "scenario": f"test_t{tnum}_{kind.lower()}",
            "passed": status.upper() == "PASS",
            "run_status": status.lower(),
        }
    return records


def filter_primary_pairs(
    matrix: dict[str, Any] | None = None,
    *,
    families: set[str] | None = None,
    tasks: set[str] | None = None,
) -> list[tuple[str, str, str]]:
    pairs = primary_pairs(matrix)
    if families:
        pairs = [p for p in pairs if p[0] in families]
    if tasks:
        pairs = [p for p in pairs if p[1] in tasks]
    return pairs


def build_paired_results(
    reference: dict[str, dict[str, Any]],
    fault: dict[str, dict[str, Any]],
    eligibility: dict[str, dict[str, bool]],
    matrix: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Merge reference + fault runs into Fxx|Tyy|O slot records."""
    matrix = matrix or load_fault_matrix()
    out: dict[str, dict[str, Any]] = {}
    for family, task, variant in primary_pairs(matrix):
        for oracle in ("O", "S", "T", "F"):
            ref_key = f"{task}|{oracle}"
            fault_key = f"{family}|{task}|{oracle}"
            ref_rec = reference.get(ref_key, {})
            fault_rec = fault.get(fault_key, {})
            eligible = eligibility.get(task, {}).get(oracle, False)
            baseline_pass = ref_rec.get("passed")
            fault_pass = fault_rec.get("passed")
            detected = (
                eligible
                and baseline_pass is True
                and fault_pass is False
            )
            out[fault_key] = {
                "fault": family,
                "task": task,
                "oracle": oracle,
                "variant": variant,
                "baseline_scenario": ref_rec.get("scenario"),
                "fault_scenario": fault_rec.get("scenario"),
                "baseline_pass": baseline_pass,
                "fault_pass": fault_pass,
                "eligible": eligible,
                "detected": detected,
            }
    return out


def patch_eligibility_for_tasks(
    eligibility: dict[str, dict[str, bool]],
    reference: dict[str, dict[str, Any]],
    tasks: set[str],
) -> dict[str, dict[str, bool]]:
    """Update eligibility for tasks present in a reference log slice."""
    updated = {tid: dict(slots) for tid, slots in eligibility.items()}
    for key, rec in reference.items():
        task = rec.get("task") or key.split("|")[0]
        if task not in tasks:
            continue
        oracle = rec.get("oracle") or key.split("|")[-1]
        updated.setdefault(task, {})[oracle] = bool(rec.get("passed"))
    return updated


def paired_slots_to_fault_results(paired: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Convert paired slots to fault_detection_results shape."""
    out: dict[str, dict[str, Any]] = {}
    for key, rec in paired.items():
        out[key] = {
            "fault": rec["fault"],
            "task": rec["task"],
            "oracle": rec["oracle"],
            "variant": rec.get("variant"),
            "scenario": rec.get("fault_scenario"),
            "passed": rec.get("fault_pass"),
            "run_status": "pass" if rec.get("fault_pass") else "fail",
            "eligible": rec.get("eligible"),
            "detected": rec.get("detected"),
        }
    return out


def detection_summary_by_family(
    paired: dict[str, dict[str, Any]],
) -> dict[str, dict[str, tuple[int, int]]]:
    """Count detected/eligible per family per oracle column."""
    counts: dict[str, dict[str, list[bool]]] = {}
    for rec in paired.values():
        fam = rec["fault"]
        oracle = rec["oracle"]
        counts.setdefault(fam, {}).setdefault(oracle, [])
        if rec.get("eligible"):
            counts[fam][oracle].append(bool(rec.get("detected")))
    summary: dict[str, dict[str, tuple[int, int]]] = {}
    for fam, cols in counts.items():
        summary[fam] = {}
        for oracle, flags in cols.items():
            summary[fam][oracle] = (sum(flags), len(flags))
    return summary
