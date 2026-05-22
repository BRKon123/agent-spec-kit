#!/usr/bin/env python3
"""One-time: parse fixed baseline_T01_T50.log → tasks/fault_detection/eligibility.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.fault_detection_lib import (  # noqa: E402
    DEFAULT_BASELINE_LOG,
    ELIGIBILITY_PATH,
    load_fault_matrix,
    parse_baseline_eligibility,
    primary_pairs,
)

REPORT_PATH = BENCH / "tasks" / "fault_detection" / "eligibility_report.md"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build eligibility.json from frozen baseline log.")
    ap.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_BASELINE_LOG,
        help="Frozen baseline log (default: baseline_T01_T50.log)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ELIGIBILITY_PATH,
        help="Output eligibility JSON path",
    )
    ap.add_argument("--report", type=Path, default=REPORT_PATH, help="Human-readable report")
    args = ap.parse_args()

    if not args.log.is_file():
        print(f"Missing baseline log: {args.log}", file=sys.stderr)
        return 1

    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    eligibility = parse_baseline_eligibility(log_text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(eligibility, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({len(eligibility)} tasks)")

    matrix = load_fault_matrix()
    lines = [
        "# Fault-detection eligibility (from frozen baseline)",
        "",
        f"Source log: `{args.log.relative_to(BENCH)}`",
        "",
        "## Primary matrix slots",
        "",
        "| Fault | Task | O | S | T | F | Eligible count |",
        "|-------|------|---|---|---|---|----------------:|",
    ]
    for family, task, _variant in primary_pairs(matrix):
        row = eligibility.get(task, {})
        flags = [row.get(o, False) for o in ("O", "S", "T", "F")]
        cells = ["Y" if f else "—" for f in flags]
        n_elig = sum(flags)
        lines.append(f"| {family} | {task} | {' | '.join(cells)} | {n_elig} |")
    lines.append("")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
