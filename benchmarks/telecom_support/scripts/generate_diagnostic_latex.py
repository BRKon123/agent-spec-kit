#!/usr/bin/env python3
"""Generate MEng_Final_Report/appendix/diagnostic_grid.tex from diagnostic_records.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
RECORDS_PATH = BENCH / "tasks" / "fault_detection" / "diagnostic_records.json"
LATEX_PATH = REPO / "MEng_Final_Report" / "appendix" / "diagnostic_grid.tex"

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.diagnostic_quality_lib import FRAMEWORKS  # noqa: E402
from scripts.generate_diagnostic_quality_table import (  # noqa: E402
    FW_ABBREV,
    _grade,
    _yn,
)

FW_ORDER = ["agent_spec_kit", "pytest_plain", "langsmith", "pydantic_evals", "promptfoo", "braintrust"]


def _latex_row(case: str, fw: str, cell: dict) -> str:
    loc = cell.get("custom_diagnostic_loc", 0)
    return (
        f"{case} & {fw} & {_grade(cell)} & {_yn(cell.get('failed_requirement_named'))} & "
        f"{_yn(cell.get('trace_node_identified'))} & {_yn(cell.get('field_path_shown'))} & "
        f"{_yn(cell.get('expected_vs_actual_shown'))} & {loc} \\\\"
    )


def generate_latex(cells: dict[str, dict]) -> str:
    by_case: dict[str, list[dict]] = {}
    for key, cell in sorted(cells.items()):
        if cell.get("framework") not in FRAMEWORKS:
            continue
        if cell.get("oracle") != "F" or not cell.get("detected"):
            continue
        case = f"{cell['family']}/{cell['task']}"
        by_case.setdefault(case, []).append(cell)

    body: list[str] = []
    for case in sorted(by_case):
        rows = by_case[case]
        fw_to_cell = {c["framework"]: c for c in rows}
        first = True
        for fw_key in FW_ORDER:
            cell = fw_to_cell.get(fw_key)
            if cell is None:
                continue
            fw = FW_ABBREV[fw_key]
            case_col = case if first else ""
            body.append(_latex_row(case_col, fw, cell))
            first = False

    lines = [
        "% Auto-generated; do not edit by hand.",
        "% Regenerate: cd benchmarks/telecom_support && uv run python scripts/generate_diagnostic_latex.py",
        "",
        "\\footnotesize",
        "\\begin{longtable}{@{}llcccccr@{}}",
        "\\caption{Diagnostic specificity on injected faults (detected, full oracle; six evaluation-library implementations). "
        "Grade uses the same A--E scale as Table~\\ref{tab:specificity-rubric}.} "
        "\\label{tab:diagnostic-injected-grid} \\\\",
        "\\toprule",
        "Case & FW & Grade & Req? & Where? & Path? & E vs A? & LOC \\\\",
        "\\midrule",
        "\\endfirsthead",
        "\\toprule",
        "Case & FW & Grade & Req? & Where? & Path? & E vs A? & LOC \\\\",
        "\\midrule",
        "\\endhead",
        *body,
        "\\bottomrule",
        "\\end{longtable}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=Path, default=RECORDS_PATH)
    ap.add_argument("--out", type=Path, default=LATEX_PATH)
    args = ap.parse_args()
    if not args.records.is_file():
        print(f"Missing {args.records}", file=sys.stderr)
        return 1
    cells = json.loads(args.records.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(generate_latex(cells), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
