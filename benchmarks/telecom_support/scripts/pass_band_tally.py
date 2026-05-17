#!/usr/bin/env python3
"""Sum stable 2/2 passes per oracle from calibration_state.json vs pass-band targets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tasks.catalog import TASK_CATALOG  # noqa: E402

STATE_PATH = _ROOT / "tasks" / "calibration_state.json"
BANDS = {"O": (45, 48), "S": (38, 42), "T": (30, 34), "F": (25, 28)}
ORACLE_KEYS = {"O": "calibration_o", "S": "calibration_s", "T": "calibration_t", "F": "calibration_f"}


def main() -> int:
    if not STATE_PATH.is_file():
        print(f"Missing {STATE_PATH}", file=sys.stderr)
        return 1
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    task_results = state.get("tasks", {})

    counts = {k: 0 for k in BANDS}
    for tid in sorted(TASK_CATALOG):
        spec = TASK_CATALOG[tid]
        for oracle, attr in ORACLE_KEYS.items():
            target = getattr(spec, attr)
            if target != "Pass":
                continue
            runs = task_results.get(f"{tid}|{oracle}", [])
            if len(runs) >= 2 and runs[0] and runs[1]:
                counts[oracle] += 1

    print("# Pass-band tally (stable 2/2 on catalog-Pass slots only)\n")
    print("| Oracle | Stable 2/2 pass | Target band | In band? |")
    print("|--------|------------------:|-------------|----------|")
    for oracle, (lo, hi) in BANDS.items():
        n = counts[oracle]
        ok = "yes" if lo <= n <= hi else "no"
        print(f"| {oracle} | {n} | {lo}–{hi} | {ok} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
