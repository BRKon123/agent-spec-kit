#!/usr/bin/env python3
"""
Build inspection_burden_manual.json: hand-reviewed field counts per diagnostic cell.

Methodology (applied case-by-case from failure boxes in INSPECTION_REVIEW.md):
- Count fields the developer must *discover* at the failure site (not fields merely
  listed as context). One unit = one leaf you still have to find by inspection.
- If the message names the offending field (e.g. sim_type, step, or a JSON path),
  that field is one unit even when a longer key list appears in the text.
- If the message is coarse (e.g. "extra key in args" with no key name, bare
  AssertionError, or "missing tool" with no index), count each candidate leaf you
  must open in the comparable object (args keys, trace tools, store rows).
- agent_spec_kit baseline uses the panel Path/Expected witness; × ask =
  ceil(ported_units / ask_units), minimum 1.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
RECORDS = BENCH / "tasks" / "fault_detection" / "diagnostic_records.json"
OUT = BENCH / "tasks" / "fault_detection" / "inspection_burden_manual.json"

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.diagnostic_quality_lib import FRAMEWORKS, inspection_ratio_display

# fmt: off
# Hand counts: (ask_units, {framework: ported_units}) per "FAMILY|TASK"
# Sources: failure_box_text in diagnostic_records.json + INSPECTION_REVIEW.md
SLOT_COUNTS: dict[str, tuple[int, dict[str, int]]] = {
    # F01/T44 — path $[0].name; ports name expected vs got tool (both named → 1)
    "F01|T44": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F02/T29 — path $[1].args.sim_type; ports also name sim_type (not “which key?” → 1)
    "F02|T29": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F02/T43 — state ticket-on-line predicate (1)
    "F02|T43": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F02/T46 — path $[1].args.step (1); ports name single forbidden arg key
    "F02|T46": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F03 — store credit count predicate (1)
    "F03|T17": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    "F03|T27": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F04/T45,T49 — three pre-auth tools (3 fields: which tool fired)
    "F04|T45": (3, {"pytest_plain": 3, "langsmith": 3, "pydantic_evals": 3, "promptfoo": 3, "braintrust": 3}),
    "F04|T49": (3, {"pytest_plain": 3, "langsmith": 3, "pydantic_evals": 3, "promptfoo": 3, "braintrust": 3}),
    # F04/T50 — output must-not-disclose rule (1)
    "F04|T50": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F05/T38 — children order: 2 named child tools; ports missing specialist → scan
    # full turn tool list (~3 top-level tools + 5 nested child tool objects ≈ 38 leaves)
    "F05|T38": (2, {"pytest_plain": 38, "langsmith": 38, "pydantic_evals": 38, "promptfoo": 38, "braintrust": 38}),
    # F07 forbid — path $[n]; ports name forbidden tool + index (pinpointed → 1)
    "F07|T29": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    "F07|T30": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    "F07|T42": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    "F07|T43": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F08/T21 — audit-note store predicate (1); bare AssertionError → audit store + trace
    # (audit_notes list empty: 1; must scan turn tools to find mutation ≈ 10 leaves)
    "F08|T21": (1, {"pytest_plain": 10, "langsmith": 10, "pydantic_evals": 10, "promptfoo": 10, "braintrust": 10}),
    # F09 — ticket store predicate (1)
    "F09|T04": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    "F09|T19": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F10/T29 — same as F02/T29 (sim_type named → 1)
    "F10|T29": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    "F10|T42": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    # F10/T43 — output rubric: 1 failed criterion in message (1); same for ports
    "F10|T43": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
    "F10|T44": (1, {"pytest_plain": 1, "langsmith": 1, "pydantic_evals": 1, "promptfoo": 1, "braintrust": 1}),
}
# fmt: on


def build_manual(records: dict) -> dict[str, dict]:
    manual: dict[str, dict] = {}
    for slot, (ask_u, ported_map) in SLOT_COUNTS.items():
        fam, task = slot.split("|")
        ask_key = f"{fam}|{task}|agent_spec_kit|F"
        manual[ask_key] = {
            "units": ask_u,
            "role": "baseline",
            "note": "agent_spec_kit panel witness",
        }
        for fw, pu in ported_map.items():
            key = f"{fam}|{task}|{fw}|F"
            ratio = inspection_ratio_display(pu, ask_u)
            manual[key] = {
                "units": pu,
                "baseline_units": ask_u,
                "ratio": ratio,
                "note": "hand-counted from failure box",
            }
    # Verify all main-table cells covered
    missing = []
    for key, cell in records.items():
        if cell.get("oracle") != "F" or not cell.get("detected"):
            continue
        if cell.get("framework") not in FRAMEWORKS:
            continue
        if key not in manual:
            missing.append(key)
    if missing:
        raise SystemExit(f"Missing manual entries: {missing}")
    return manual


def main() -> int:
    records = json.loads(RECORDS.read_text(encoding="utf-8"))
    manual = build_manual(records)
    OUT.write_text(json.dumps(manual, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(manual)} entries to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
