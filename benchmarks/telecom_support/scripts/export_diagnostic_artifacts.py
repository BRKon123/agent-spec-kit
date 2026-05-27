#!/usr/bin/env python3
"""Bundle trace JSONL + store snapshots + log witnesses into per-slot artifact JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from diagnostic_comparison.shared.artifact_io import (
    ARTIFACT_DIR,
    SNAPSHOT_DIR,
    TRACE_DIR,
    parse_tools_from_witness_actual,
    slot_artifact_path,
)
from scripts.diagnostic_quality_lib import load_results_enriched, parse_failure_panels
from scripts.fault_detection_lib import (
    DEFAULT_FAULT_LOG,
    ELIGIBILITY_PATH,
    RESULTS_PATH,
)

from store.snapshot import dump_store_state
from store.seeds import apply_seed
from store.store import TelcoStore
import shutil
import tempfile


def _load_trace_turns(scenario: str) -> list[dict]:
    path = TRACE_DIR / f"{scenario}.jsonl"
    if not path.is_file():
        return []
    turns: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        turns.append(
            {
                "turn_index": rec.get("turn_index"),
                "user_message": rec.get("user_message", ""),
                "tools": rec.get("tools") or [],
                "status": rec.get("status"),
            }
        )
    return turns


def _load_snapshot(scenario: str, seed: str) -> dict | None:
    path = SNAPSHOT_DIR / f"{scenario}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    # Fallback: fresh seed only (state checks may not reproduce failure)
    base = Path(tempfile.mkdtemp(prefix="telco_export_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, seed)
        snap = dump_store_state(telco)
        snap["_note"] = "seed-only fallback; re-run fault detection with TELCO_STORE_SNAPSHOT_DIR for full state"
        return snap
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=DEFAULT_FAULT_LOG)
    ap.add_argument("--results", type=Path, default=RESULTS_PATH)
    ap.add_argument("--eligibility", type=Path, default=ELIGIBILITY_PATH)
    args = ap.parse_args()

    if not args.log.is_file():
        print(f"Missing log: {args.log}", file=sys.stderr)
        return 1
    if not args.results.is_file():
        print(f"Missing results: {args.results}", file=sys.stderr)
        return 1

    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    panels = parse_failure_panels(log_text)
    results = load_results_enriched(args.results, args.eligibility)

    f_detected: set[tuple[str, str]] = set()
    for rec in results.values():
        if rec.get("detected") and rec.get("oracle") == "F":
            f_detected.add((rec["fault"], rec["task"]))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for family, task in sorted(f_detected):
        scenario = f"test_{family.lower()}_t{task[1:].lower()}_full"
        witness = panels.get(scenario)
        if witness is None:
            continue
        seed = f"task_{task}"
        turns = _load_trace_turns(scenario)
        snapshot = _load_snapshot(scenario, seed)
        final_tools = turns[-1]["tools"] if turns else []
        if not final_tools and witness.actual:
            final_tools = parse_tools_from_witness_actual(witness.actual)
        final_output = witness.output_text or ""
        artifact = {
            "family": family,
            "task": task,
            "scenario": scenario,
            "seed": seed,
            "witness_check": witness.check,
            "witness_where": witness.where,
            "witness_path": witness.path,
            "witness_expected": witness.expected,
            "witness_actual": witness.actual,
            "witness_state_message": witness.state_message,
            "turns": turns,
            "final_tools": final_tools,
            "final_output": final_output,
            "store_snapshot": snapshot,
        }
        out = slot_artifact_path(family, task)
        out.write_text(json.dumps(artifact, indent=2, default=str) + "\n", encoding="utf-8")
        count += 1

    print(f"Wrote {count} artifacts under {ARTIFACT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
