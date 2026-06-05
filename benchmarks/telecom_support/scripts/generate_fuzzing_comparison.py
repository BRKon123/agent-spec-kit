#!/usr/bin/env python3
"""Compare deterministic-operator fuzz results with LLM-mutation fuzz results."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

BENCH_SCR = Path(__file__).resolve().parents[1]
if str(BENCH_SCR) not in sys.path:
    sys.path.insert(0, str(BENCH_SCR))

from fuzzing_study_lib import BENCH, load_study_config


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "conversations": len(records),
        "unique_tool_paths": len({r["tool_path_signature"] for r in records}),
        "distinct_failure_signatures": len(
            {r["failure_signature"] for r in records if r["failure_signature"]}
        ),
        "failing_conversations": sum(1 for r in records if r.get("failure_signature")),
        "median_turns": median([r["turn_count"] for r in records]) if records else 0,
    }


def _fuzz_records(study: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in study.get("records", []) if r.get("method") == "fuzz"]


def _operator_failures(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for r in records:
        if r.get("failure_signature"):
            counts[str(r.get("mutation_operator") or "unknown")] += 1
    return counts


def _failure_signatures(records: list[dict[str, Any]]) -> set[str]:
    return {str(r["failure_signature"]) for r in records if r.get("failure_signature")}


def _per_task_failures(records: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for r in records:
        if r.get("failure_signature"):
            out[str(r["task_id"])] += 1
    return dict(sorted(out.items()))


def generate_comparison(
    *,
    deterministic: dict[str, Any],
    llm: dict[str, Any],
) -> str:
    det_fuzz = _fuzz_records(deterministic)
    llm_fuzz = _fuzz_records(llm)
    det_agg = _aggregate(det_fuzz)
    llm_agg = _aggregate(llm_fuzz)
    det_sigs = _failure_signatures(det_fuzz)
    llm_sigs = _failure_signatures(llm_fuzz)
    only_det = sorted(det_sigs - llm_sigs)
    only_llm = sorted(llm_sigs - det_sigs)
    shared = sorted(det_sigs & llm_sigs)

    lines = [
        "# Fuzzing Study Comparison: Deterministic vs LLM Mutations",
        "",
        f"- Deterministic run id: {deterministic.get('run_id', 'n/a')}",
        f"- LLM run id: {llm.get('run_id', 'n/a')}",
        f"- LLM mutation backend: {llm.get('mutation_backend', 'llm')}",
        "",
        "## Fuzz-arm summary",
        "",
        "| Backend | Conversations | Failing | Unique tool paths | Distinct failure signatures | Median turns |",
        "|---------|--------------:|--------:|------------------:|----------------------------:|-------------:|",
        f"| Deterministic operators | {det_agg['conversations']} | {det_agg['failing_conversations']} | "
        f"{det_agg['unique_tool_paths']} | {det_agg['distinct_failure_signatures']} | {det_agg['median_turns']} |",
        f"| LLM mutations | {llm_agg['conversations']} | {llm_agg['failing_conversations']} | "
        f"{llm_agg['unique_tool_paths']} | {llm_agg['distinct_failure_signatures']} | {llm_agg['median_turns']} |",
        "",
        "## Failure-signature overlap",
        "",
        f"- Shared signatures: {len(shared)}",
        f"- Deterministic-only signatures: {len(only_det)}",
        f"- LLM-only signatures: {len(only_llm)}",
        "",
        "## Operator-level fuzz failures",
        "",
        "### Deterministic",
        "",
    ]
    for op, n in _operator_failures(det_fuzz).most_common():
        lines.append(f"- `{op}`: {n}")
    lines.extend(["", "### LLM", ""])
    for op, n in _operator_failures(llm_fuzz).most_common():
        lines.append(f"- `{op}`: {n}")

    lines.extend(["", "## Per-task failing conversations", "", "### Deterministic", ""])
    for task, n in _per_task_failures(det_fuzz).items():
        lines.append(f"- {task}: {n}")
    lines.extend(["", "### LLM", ""])
    for task, n in _per_task_failures(llm_fuzz).items():
        lines.append(f"- {task}: {n}")

    if only_llm:
        lines.extend(["", "## Sample LLM-only failure signatures", ""])
        for sig in only_llm[:8]:
            lines.append(f"- {sig}")
    if only_det:
        lines.extend(["", "## Sample deterministic-only failure signatures", ""])
        for sig in only_det[:8]:
            lines.append(f"- {sig}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Both arms reuse the same operator catalogue as mutation *intents*: deterministic code applied "
            "regex/string transforms directly, while the LLM arm asks the model to realise those intents on "
            "the manual seed transcript. Manual and simulation arms are unchanged between runs.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    cfg = load_study_config()
    outputs = cfg.get("outputs") or {}
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--deterministic-json",
        type=Path,
        default=BENCH / outputs.get("deterministic_baseline_json", "tasks/fuzzing/fuzzing_runs_deterministic.json"),
    )
    ap.add_argument(
        "--llm-json",
        type=Path,
        default=BENCH / outputs.get("study_json", "tasks/fuzzing/fuzzing_runs.json"),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=BENCH / outputs.get("comparison_md", "tasks/fuzzing/fuzzing_study_comparison.md"),
    )
    args = ap.parse_args()
    deterministic = json.loads(args.deterministic_json.read_text(encoding="utf-8"))
    llm = json.loads(args.llm_json.read_text(encoding="utf-8"))
    args.out.write_text(generate_comparison(deterministic=deterministic, llm=llm) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
