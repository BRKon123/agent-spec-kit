#!/usr/bin/env python3
"""Print failure taxonomy counts using structural equivalence keys."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from study_failure_signatures import equivalence_key_from_record


def _keys(records: list[dict], method: str) -> set[tuple]:
    subset = [r for r in records if r.get("method") == method and r.get("failure_signature")]
    return {k for r in subset if (k := equivalence_key_from_record(r)) is not None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--study-json",
        default="tasks/fuzzing/fuzzing_runs.json",
    )
    args = ap.parse_args()
    path = Path(args.study_json)
    if not path.is_absolute():
        path = BENCH / path
    study = json.loads(path.read_text(encoding="utf-8"))
    records = study.get("records") or []

    manual = _keys(records, "manual")
    sim = _keys(records, "sim")
    fuzz = _keys(records, "fuzz")

    manual_fail = len([r for r in records if r.get("method") == "manual" and r.get("failure_signature")])
    sim_fail = len([r for r in records if r.get("method") == "sim" and r.get("failure_signature")])
    fuzz_fail = len([r for r in records if r.get("method") == "fuzz" and r.get("failure_signature")])

    sim_new_manual = len(sim - manual)
    sim_new_fuzz = len(sim - fuzz)
    fuzz_new_manual = len(fuzz - manual)
    fuzz_new_sim = len(fuzz - sim)
    overlap_sim_fuzz = len(sim & fuzz)

    print(f"manual: distinct={len(manual)} convs={manual_fail}")
    print(f"sim: distinct={len(sim)} convs={sim_fail}")
    print(f"fuzz: distinct={len(fuzz)} convs={fuzz_fail}")
    print(f"sim new vs manual: {sim_new_manual}")
    print(f"sim new vs fuzz: {sim_new_fuzz}")
    print(f"fuzz new vs manual: {fuzz_new_manual}")
    print(f"fuzz new vs sim: {fuzz_new_sim}")
    print(f"sim ∩ fuzz shared families: {overlap_sim_fuzz}")
    print(f"total failing convs: {manual_fail + sim_fail + fuzz_fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
