#!/usr/bin/env python3
"""Generate FAULT_DETECTION_TABLE.md and FAULT_DIAGNOSTICS.md from real run JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
FAULT_DIR = BENCH / "tasks" / "fault_detection"
TABLE_PATH = FAULT_DIR / "FAULT_DETECTION_TABLE.md"
DIAG_PATH = FAULT_DIR / "FAULT_DIAGNOSTICS.md"
BASELINE_REPORT = BENCH / "tasks" / "calibration_logs" / "baseline_report.md"

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.fault_detection_lib import (  # noqa: E402
    ELIGIBILITY_PATH,
    META_PATH,
    RESULTS_PATH,
    load_fault_matrix,
    primary_pairs,
)


def _cell_status(rec: dict[str, object] | None, eligible: bool) -> str:
    if not eligible:
        return "N/A"
    if rec is None or rec.get("run_status") == "incomplete" or rec.get("passed") is None:
        return "incomplete"
    if rec.get("detected"):
        return "detected"
    return "missed"


def _summary_rates(
    results: dict[str, dict[str, object]],
    eligibility: dict[str, dict[str, bool]],
    matrix: dict,
) -> dict[str, dict[str, tuple[int, int, float | None]]]:
    """fault -> oracle -> (detected, eligible, pct)."""
    out: dict[str, dict[str, tuple[int, int, float | None]]] = {}
    for family, _task, _ in primary_pairs(matrix):
        out.setdefault(family, {})
        for oracle in "O", "S", "T", "F":
            det = elig = 0
            for fam2, task, _ in primary_pairs(matrix):
                if fam2 != family:
                    continue
                key = f"{family}|{task}|{oracle}"
                if not eligibility.get(task, {}).get(oracle, False):
                    continue
                elig += 1
                rec = results.get(key)
                if rec and rec.get("detected"):
                    det += 1
            pct = (100.0 * det / elig) if elig else None
            out[family][oracle] = (det, elig, pct)
    return out


def generate_table(
    results: dict[str, dict[str, object]],
    eligibility: dict[str, dict[str, bool]],
    meta: dict[str, object],
    matrix: dict,
) -> str:
    summary = _summary_rates(results, eligibility, matrix)
    now = datetime.now(UTC).isoformat()
    lines = [
        "# Fault detection table (F01–F10)",
        "",
        "Generated from real fault-detection run data. Regenerate:",
        "",
        "```bash",
        "uv run python benchmarks/telecom_support/scripts/generate_fault_detection_table.py",
        "```",
        "",
        f"- Generated: {now}",
        f"- Fault log: `{meta.get('log_path', '—')}`",
        f"- Matrix hash: `{meta.get('matrix_hash', '—')}`",
        f"- Run exit code: `{meta.get('exit_code', '—')}`",
        f"- Parsed scenarios: `{meta.get('parsed_from_log', '—')}` / `{meta.get('scenario_count', '—')}`",
        f"- Baseline (frozen): `{BASELINE_REPORT.relative_to(BENCH)}`",
        "",
        "## Summary (detection rate = detected / eligible)",
        "",
        "| Fault | O | S | T | F |",
        "|-------|---|---|---|---|",
    ]
    for family in sorted(summary.keys()):
        cells = []
        for oracle in "O", "S", "T", "F":
            det, elig, pct = summary[family][oracle]
            if pct is None:
                cells.append("—")
            else:
                cells.append(f"{det}/{elig} ({pct:.0f}%)")
        lines.append(f"| {family} | {' | '.join(cells)} |")

    lines.extend(
        [
            "",
            "## Detail grid (primary matrix)",
            "",
            "Legend: **detected** = eligible and fault scenario failed; **missed** = eligible but passed; **N/A** = reference failed baseline; **incomplete** = no run line.",
            "",
            "| Fault | Task | O | S | T | F |",
            "|-------|------|---|---|---|---|",
        ]
    )
    for family, task, _ in primary_pairs(matrix):
        row = [family, task]
        for oracle in "O", "S", "T", "F":
            key = f"{family}|{task}|{oracle}"
            elig = eligibility.get(task, {}).get(oracle, False)
            row.append(_cell_status(results.get(key), elig))
        lines.append(f"| {' | '.join(row)} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Denominator uses only task×oracle slots where the **frozen unsteered reference** passed (`eligibility.json` from `baseline_T01_T50.log`).",
            "- Reference agent and baseline artifacts are not re-run or modified by this pipeline.",
            "- Sparse columns (e.g. F01/T on T03, T44) reflect baseline gaps, not missing fault injection.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_diagnostics(
    results: dict[str, dict[str, object]],
    eligibility: dict[str, dict[str, bool]],
    matrix: dict,
) -> str:
    lines = [
        "# Fault detection diagnostics",
        "",
        "Exemplar tasks from `fault_matrix.yaml` — measured from fault run log only.",
        "",
    ]
    diagnostics = matrix.get("diagnostics", {})
    families = matrix.get("families", {})
    for family in sorted(diagnostics.keys()):
        tasks = diagnostics[family]
        spec = families.get(family, {})
        lines.append(f"## {family}: {spec.get('description', '')}")
        lines.append("")
        for task in tasks:
            lines.append(f"### {task}")
            lines.append("")
            lines.append("| Oracle | Eligible | Fault pass | Detected |")
            lines.append("|--------|----------|------------|----------|")
            for oracle in "O", "S", "T", "F":
                key = f"{family}|{task}|{oracle}"
                rec = results.get(key, {})
                elig = eligibility.get(task, {}).get(oracle, False)
                passed = rec.get("passed")
                pass_s = "—" if passed is None else ("yes" if passed else "no")
                det = rec.get("detected", False) if elig else False
                lines.append(
                    f"| {oracle} | {'yes' if elig else 'no'} | {pass_s} | "
                    f"{'yes' if det else 'no' if elig else '—'} |"
                )
            snippet = rec.get("failure_excerpt") if isinstance(rec, dict) else None
            if snippet:
                lines.append("")
                lines.append(f"Failure excerpt: `{snippet}`")
            lines.append("")
        intent = spec.get("design_intent", {})
        if intent:
            lines.append("*Design intent (not measured):*")
            for k, v in intent.items():
                lines.append(f"- {k}: {v}")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=RESULTS_PATH)
    ap.add_argument("--eligibility", type=Path, default=ELIGIBILITY_PATH)
    ap.add_argument("--matrix", type=Path, default=BENCH / "tasks" / "fault_matrix.yaml")
    args = ap.parse_args()

    if not args.results.is_file():
        print(f"Missing results: {args.results}", file=sys.stderr)
        return 1
    if not args.eligibility.is_file():
        print(f"Missing eligibility: {args.eligibility}", file=sys.stderr)
        return 1

    results = json.loads(args.results.read_text(encoding="utf-8"))
    if not results:
        print("fault_detection_results.json is empty", file=sys.stderr)
        return 1

    eligibility = json.loads(args.eligibility.read_text(encoding="utf-8"))
    matrix = load_fault_matrix(args.matrix)
    expected = set()
    for family, task, _ in primary_pairs(matrix):
        for oracle in "O", "S", "T", "F":
            expected.add(f"{family}|{task}|{oracle}")

    missing = [k for k in sorted(expected) if k not in results]
    if missing and all(results.get(k, {}).get("run_status") != "incomplete" for k in missing):
        # Allow incomplete markers from parser
        incomplete = [k for k in missing if results.get(k, {}).get("run_status") == "incomplete"]
        if len(incomplete) != len(missing):
            print(f"Missing {len(missing)} primary slots in results (first 5): {missing[:5]}", file=sys.stderr)
            return 1

    meta: dict[str, object] = {}
    if META_PATH.is_file():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    TABLE_PATH.write_text(
        generate_table(results, eligibility, meta, matrix),
        encoding="utf-8",
    )
    DIAG_PATH.write_text(
        generate_diagnostics(results, eligibility, matrix),
        encoding="utf-8",
    )
    print(f"Wrote {TABLE_PATH}")
    print(f"Wrote {DIAG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
