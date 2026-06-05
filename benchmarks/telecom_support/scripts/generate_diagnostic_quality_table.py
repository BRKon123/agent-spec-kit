#!/usr/bin/env python3
"""Generate DIAGNOSTIC_QUALITY_TABLE.md from diagnostic_records.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
TABLE_PATH = BENCH / "tasks" / "fault_detection" / "DIAGNOSTIC_QUALITY_TABLE.md"
RECORDS_PATH = BENCH / "tasks" / "fault_detection" / "diagnostic_records.json"
META_PATH = BENCH / "tasks" / "fault_detection" / "diagnostic_extract_meta.json"
EXEMPLARS_PATH = BENCH / "tasks" / "fault_detection" / "diagnostic_exemplars.yaml"

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.diagnostic_quality_lib import (
    DIAGNOSTIC_SPECIFICITY_RUBRIC,
    FRAMEWORKS,
    backfill_specificity_grades,
    specificity_grade,
)

FW_ABBREV = {
    "agent_spec_kit": "ask",
    "pytest_plain": "py",
    "langsmith": "ls",
    "pydantic_evals": "pe",
    "promptfoo": "pf",
    "braintrust": "bt",
}


def _yn(val: object) -> str:
    return "Yes" if val else "No"


def _grade(cell: dict) -> str:
    if cell.get("status") == "llm_error":
        return "ERR"
    if cell.get("status") == "no_failure_box":
        return "—"
    g = specificity_grade(cell)
    return g if g != "—" else "—"


def _rows(cells: dict[str, dict], *, section: str | None = None) -> list[dict]:
    out = []
    for key, cell in sorted(cells.items()):
        if section and cell.get("section") != section:
            continue
        if section is None and cell.get("section") == "oracle_ceiling":
            continue
        out.append(cell)
    return out


def generate_table(cells: dict[str, dict], meta: dict) -> str:
    now = datetime.now(UTC).isoformat()
    lines = [
        "# Diagnostic quality table",
        "",
        f"- Generated: {now}",
        f"- Records: `{RECORDS_PATH.relative_to(BENCH)}`",
        f"- LLM model: `{meta.get('model', '—')}`",
        f"- Cells scored OK: `{meta.get('scored_ok', '—')}` / `{meta.get('cell_count', '—')}`",
        "",
        "Regenerate:",
        "",
        "```bash",
        "cd benchmarks/telecom_support",
        "uv run python scripts/collect_diagnostic_failures.py",
        "OPENAI_API_KEY=... uv run python scripts/extract_diagnostic_quality.py",
        "uv run python scripts/generate_diagnostic_quality_table.py",
        "uv run python scripts/generate_diagnostic_latex.py",
        "```",
        "",
        "## Specificity rubric (A–E)",
        "",
        DIAGNOSTIC_SPECIFICITY_RUBRIC,
        "",
        "## Section A — Oracle diagnostic ceiling (agent_spec_kit)",
        "",
        "For F-detected tasks, failures under O/S/T/F oracles.",
        "",
        "| Case | Oracle | Grade | Failed req? | Where? | Path? | E vs A? | LOC |",
        "|------|--------|:-----:|:-----------:|:------:|:-----:|:-------:|----:|",
    ]
    for cell in _rows(cells, section="oracle_ceiling"):
        case = f"{cell['family']}/{cell['task']}"
        lines.append(
            f"| {case} | {cell['oracle']} | {_grade(cell)} | {_yn(cell.get('failed_requirement_named'))} | "
            f"{_yn(cell.get('trace_node_identified'))} | {_yn(cell.get('field_path_shown'))} | "
            f"{_yn(cell.get('expected_vs_actual_shown'))} | "
            f"{cell.get('custom_diagnostic_loc', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Section B — Main table (detected, full oracle, six frameworks)",
            "",
            "| Case | Framework | Grade | Failed req? | Where? | Path? | E vs A? | LOC |",
            "|------|-----------|:-----:|:-----------:|:------:|:-----:|:-------:|----:|",
        ]
    )
    for cell in _rows(cells):
        if cell.get("framework") not in FRAMEWORKS:
            continue
        if cell.get("oracle") != "F" or not cell.get("detected"):
            continue
        case = f"{cell['family']}/{cell['task']}"
        fw = FW_ABBREV.get(cell["framework"], cell["framework"])
        lines.append(
            f"| {case} | {fw} | {_grade(cell)} | {_yn(cell.get('failed_requirement_named'))} | "
            f"{_yn(cell.get('trace_node_identified'))} | {_yn(cell.get('field_path_shown'))} | "
            f"{_yn(cell.get('expected_vs_actual_shown'))} | "
            f"{cell.get('custom_diagnostic_loc', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Section C — Qualitative examples",
            "",
            "Configure slots in `diagnostic_exemplars.yaml` to render side-by-side snippets here.",
            "",
            "## Conclusion (template)",
            "",
            "Richer oracles and frameworks that surface trace, state, and matcher witnesses "
            "produce more localised failure messages. Output-only or generic assertion shells "
            "tend toward lower specificity grades on the same underlying faults.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=Path, default=RECORDS_PATH)
    ap.add_argument(
        "--write-back-grades",
        action="store_true",
        help="Persist specificity_grade in diagnostic_records.json from legacy 0-4 scores.",
    )
    args = ap.parse_args()
    if not args.records.is_file():
        print(f"Missing {args.records}", file=sys.stderr)
        return 1
    cells = json.loads(args.records.read_text(encoding="utf-8"))
    n = backfill_specificity_grades(cells)
    if args.write_back_grades and n:
        args.records.write_text(
            json.dumps(cells, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Backfilled specificity_grade on {n} cells in {args.records}")
    meta = {}
    if META_PATH.is_file():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    TABLE_PATH.write_text(generate_table(cells, meta), encoding="utf-8")
    print(f"Wrote {TABLE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
