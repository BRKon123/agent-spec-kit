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
from study_failure_signatures import equivalence_key_from_record


def _authoring_effort(method: str, *, mutation_backend: str | None = None) -> str:
    if method == "manual":
        return "Manual script (canonical seed)"
    if method == "sim":
        return "Task profile + persona seed"
    if mutation_backend == "llm":
        return "Manual seed + LLM mutation intents"
    return "Manual seed + mutation operator"


def generate_markdown(study: dict[str, Any]) -> str:
    records = study["records"]
    tasks = len({r["task_id"] for r in records if r["method"] == "manual"})
    manual = study["summary"]["manual"]
    sim = study["summary"]["sim"]
    fuzz = study["summary"]["fuzz"]
    mutation_backend = study.get("mutation_backend")
    lines = [
        "# Fuzzing Study",
        "",
        f"- Generated: {study['generated_utc']}",
        f"- Run id: {study.get('run_id', 'n/a')}",
        f"- Tasks: {', '.join(study['selected_tasks'])}",
        f"- Mutation backend: {mutation_backend or 'deterministic'}",
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
            f"{s['distinct_failure_signatures']} | {s['median_turns']} | "
            f"{_authoring_effort(key, mutation_backend=mutation_backend if key == 'fuzz' else None)} |"
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
            (
                "Fuzzing applies mutation intents over valid manual-script user turns and reuses the "
                "same F-oracle as user simulation. In this run, mutations are produced by an LLM rather "
                "than deterministic regex/string operators."
                if mutation_backend == "llm"
                else "Fuzzing applies generic mutation operators over valid manual-script user turns and reuses the "
                "same F-oracle as user simulation. It tests whether small transcript perturbations surface "
                "tool-path and failure-signature diversity beyond manual scripts and persona-based simulation."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _equiv_keys(records: list[dict[str, Any]], method: str) -> set[tuple[Any, ...]]:
    out: set[tuple[Any, ...]] = set()
    for r in records:
        if r.get("method") != method:
            continue
        key = equivalence_key_from_record(r)
        if key is not None:
            out.add(key)
    return out


def build_fuzz_new_failures(study: dict[str, Any]) -> dict[str, Any]:
    records = study["records"]
    known = _equiv_keys(records, "sim") | _equiv_keys(records, "manual")
    new_rows = []
    for r in records:
        if r["method"] != "fuzz":
            continue
        key = equivalence_key_from_record(r)
        if key is not None and key not in known:
            new_rows.append(
                {
                    "task_id": r["task_id"],
                    "mutation_operator": r.get("mutation_operator"),
                    "framework_trial_index": r.get("framework_trial_index"),
                    "failure_equivalence_key": list(key),
                    "failure_signature": r.get("failure_signature"),
                    "tool_path_signature": r.get("tool_path_signature"),
                    "case_id": r.get("case_id"),
                }
            )
    return {"fuzz_new_failures": new_rows, "count": len(new_rows)}


def build_failure_signatures(study: dict[str, Any]) -> dict[str, Any]:
    by_method: dict[str, list[list[Any]]] = defaultdict(list)
    for r in study["records"]:
        key = equivalence_key_from_record(r)
        if key is not None:
            by_method[r["method"]].append(list(key))
    return {m: sorted(sigs) for m, sigs in by_method.items()}


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
