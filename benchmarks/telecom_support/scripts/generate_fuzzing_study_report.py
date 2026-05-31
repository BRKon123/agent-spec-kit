#!/usr/bin/env python3
"""Generate fuzzing_study.md and signature artifacts from fuzzing_runs.json."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BENCH_SCR = Path(__file__).resolve().parents[1]
if str(BENCH_SCR) not in sys.path:
    sys.path.insert(0, str(BENCH_SCR))

from fuzzing_study_lib import BENCH


def _authoring_effort(method: str) -> str:
    if method == "manual":
        return "Manual script (canonical seed)"
    if method == "sim":
        return "Task profile + persona seed"
    return "Manual seed + mutation operator"


def generate_markdown(study: dict[str, Any]) -> str:
    records = study["records"]
    tasks = len({r["task_id"] for r in records if r["method"] == "manual"})
    manual = study["summary"]["manual"]
    sim = study["summary"]["sim"]
    fuzz = study["summary"]["fuzz"]
    lines = [
        "# Fuzzing Study",
        "",
        f"- Generated: {study['generated_utc']}",
        f"- Run id: {study.get('run_id', 'n/a')}",
        f"- Tasks: {', '.join(study['selected_tasks'])}",
        f"- Calibration steering: {study.get('calibration_steering', False)}",
        "",
        "## Primary comparison",
        "",
        "| Method | Tasks | Conversations | Unique tool paths | Distinct failure signatures | Median turns | Authoring |",
        "|--------|------:|--------------:|------------------:|----------------------------:|-------------:|-----------|",
    ]
    for key, label in (
        ("manual", "Manual scripts"),
        ("sim", "User simulation"),
        ("fuzz", "Mutation fuzz"),
    ):
        s = study["summary"][key]
        lines.append(
            f"| {label} | {tasks} | {s['conversations']} | {s['unique_tool_paths']} | "
            f"{s['distinct_failure_signatures']} | {s['median_turns']} | {_authoring_effort(key)} |"
        )
    lines.extend(
        [
            "",
            "## Operator-level fuzz failures",
            "",
        ]
    )
    op_counts: Counter[str] = Counter()
    for r in records:
        if r["method"] == "fuzz" and r.get("failure_signature"):
            op_counts[str(r.get("mutation_operator") or "unknown")] += 1
    for op, n in op_counts.most_common():
        lines.append(f"- `{op}`: {n} failing conversations")
    lines.extend(
        [
            "",
            "## Claim",
            "",
            "Fuzzing applies generic mutation operators over valid manual-script user turns and reuses the "
            "same F-oracle as user simulation. It tests whether small transcript perturbations surface "
            "tool-path and failure-signature diversity beyond manual scripts and persona-based simulation.",
            "",
        ]
    )
    return "\n".join(lines)


def build_fuzz_new_failures(study: dict[str, Any]) -> dict[str, Any]:
    sim_sigs: set[str] = set()
    manual_sigs: set[str] = set()
    for r in study["records"]:
        sig = r.get("failure_signature")
        if not sig:
            continue
        if r["method"] == "sim":
            sim_sigs.add(sig)
        elif r["method"] == "manual":
            manual_sigs.add(sig)
    known = sim_sigs | manual_sigs
    new_rows = []
    for r in study["records"]:
        if r["method"] != "fuzz":
            continue
        sig = r.get("failure_signature")
        if sig and sig not in known:
            new_rows.append(
                {
                    "task_id": r["task_id"],
                    "mutation_operator": r.get("mutation_operator"),
                    "framework_trial_index": r.get("framework_trial_index"),
                    "failure_signature": sig,
                    "tool_path_signature": r.get("tool_path_signature"),
                    "case_id": r.get("case_id"),
                }
            )
    return {"fuzz_new_failures": new_rows, "count": len(new_rows)}


def build_failure_signatures(study: dict[str, Any]) -> dict[str, Any]:
    by_method: dict[str, list[str]] = defaultdict(list)
    for r in study["records"]:
        sig = r.get("failure_signature")
        if sig:
            by_method[r["method"]].append(sig)
    return {m: sorted(set(sigs)) for m, sigs in by_method.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--study-json",
        type=Path,
        default=BENCH / "tasks" / "fuzzing" / "fuzzing_runs.json",
    )
    args = ap.parse_args()
    study = json.loads(args.study_json.read_text(encoding="utf-8"))
    out_dir = BENCH / "tasks" / "fuzzing"
    (out_dir / "fuzzing_study.md").write_text(generate_markdown(study) + "\n", encoding="utf-8")
    (out_dir / "fuzz_failure_signatures.json").write_text(
        json.dumps(build_failure_signatures(study), indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "fuzz_new_failures.json").write_text(
        json.dumps(build_fuzz_new_failures(study), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_dir / 'fuzzing_study.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
