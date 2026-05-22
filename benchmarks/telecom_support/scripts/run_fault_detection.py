#!/usr/bin/env python3
"""Run fault-detection matrix and parse log → fault_detection_results.json."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
FAULT_SCENARIOS_DIR = BENCH / "tasks" / "fault_detection" / "generated"

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.fault_detection_lib import (  # noqa: E402
    DEFAULT_FAULT_LOG,
    ELIGIBILITY_PATH,
    META_PATH,
    RESULTS_PATH,
    enrich_detection,
    expected_scenario_names,
    load_fault_matrix,
    matrix_file_hash,
    parse_fault_detection_log,
    primary_pairs,
    variant_for_pair,
)

ENV_DISABLE_STEERING = {**os.environ, "TELCO_DISABLE_CALIBRATION_STEERING": "1"}


def _run_agent_spec_kit(log_path: Path, *, workers: int, primary_only: bool) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "uv",
        "run",
        "agent-spec-kit",
        "run",
        str(FAULT_SCENARIOS_DIR),
        "--tags",
        "fault-detection",
        "-n",
        str(workers),
    ]
    header = (
        f"# fault-detection run {datetime.now(UTC).isoformat()}\n"
        f"# matrix_hash={matrix_file_hash()}\n"
    )
    with log_path.open("w", encoding="utf-8") as logf:
        logf.write(header)
        logf.flush()
        proc = subprocess.run(
            cmd,
            cwd=REPO,
            env=ENV_DISABLE_STEERING,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
        )
    return proc.returncode


def _write_results(
    log_path: Path,
    *,
    exit_code: int,
    eligibility_path: Path,
) -> dict[str, dict[str, object]]:
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    raw = parse_fault_detection_log(log_text)
    eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
    enriched = enrich_detection(raw, eligibility)

    matrix = load_fault_matrix()
    for family, task, _ in primary_pairs(matrix):
        variant = variant_for_pair(matrix, family, task)
        for kind, oracle in [("full", "F"), ("trace", "T"), ("state", "S"), ("output", "O")]:
            fnum = family[1:]
            tnum = task[1:]
            key = f"{family}|{task}|{oracle}"
            if key not in enriched:
                enriched[key] = {
                    "fault": family,
                    "task": task,
                    "oracle": oracle,
                    "variant": variant,
                    "scenario": f"test_f{fnum}_t{tnum}_{kind}",
                    "passed": None,
                    "run_status": "incomplete",
                    "eligible": eligibility.get(task, {}).get(oracle, False),
                    "detected": False,
                }
            else:
                enriched[key]["variant"] = variant

    meta = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "log_path": str(log_path.relative_to(BENCH)),
        "exit_code": exit_code,
        "matrix_hash": matrix_file_hash(),
        "scenario_count": len(enriched),
        "parsed_from_log": len(raw),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return enriched


def main() -> int:
    ap = argparse.ArgumentParser(description="Run and/or parse fault-detection matrix.")
    ap.add_argument("--log", type=Path, default=DEFAULT_FAULT_LOG, help="Fault run log path")
    ap.add_argument(
        "--eligibility",
        type=Path,
        default=ELIGIBILITY_PATH,
        help="Committed eligibility.json",
    )
    ap.add_argument("--workers", type=int, default=4, help="Parallel workers for agent-spec-kit")
    ap.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse existing log only (no agent run)",
    )
    ap.add_argument(
        "--run",
        action="store_true",
        help="Execute agent-spec-kit fault-detection scenarios",
    )
    args = ap.parse_args()

    if not args.eligibility.is_file():
        print(f"Missing eligibility.json: {args.eligibility}", file=sys.stderr)
        print("Run: uv run python benchmarks/telecom_support/scripts/build_fault_eligibility.py", file=sys.stderr)
        return 1

    exit_code = 0
    if args.run or not args.parse_only:
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            print("OPENAI_API_KEY not set; use --parse-only with an existing log.", file=sys.stderr)
            return 1
        exit_code = _run_agent_spec_kit(args.log, workers=args.workers, primary_only=True)
        print(f"agent-spec-kit exit_code={exit_code}; log={args.log}")

    if not args.log.is_file():
        print(f"Missing log: {args.log}", file=sys.stderr)
        return 1

    enriched = _write_results(args.log, exit_code=exit_code, eligibility_path=args.eligibility)
    print(f"Wrote {RESULTS_PATH} ({len(enriched)} slots)")
    print(f"Wrote {META_PATH}")
    return 0 if exit_code == 0 else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
