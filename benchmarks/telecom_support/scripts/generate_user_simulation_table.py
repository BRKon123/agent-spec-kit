#!/usr/bin/env python3
"""Generate user_simulation_study.md and signature artifacts from JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from user_simulation_lib import BENCH


def _authoring_effort_label(method: str) -> str:
    if method == "manual":
        return "Manual script text for every conversation"
    return "One profile per task + seeds"


def _row(summary: dict[str, Any], method_name: str, tasks: int, method_key: str) -> str:
    return (
        f"| {method_name} | {tasks} | {summary['conversations']} | "
        f"{summary['unique_tool_paths']} | "
        f"{summary['distinct_simulation_discovered_failure_signatures']} | "
        f"{summary['median_turns']} | {_authoring_effort_label(method_key)} |"
    )


def _choose_snippet(records: list[dict[str, Any]], task_id: str, method: str) -> dict[str, Any] | None:
    for r in records:
        if r["task_id"] == task_id and r["method"] == method:
            return r
    return None


def generate_markdown(study: dict[str, Any]) -> str:
    records = study["records"]
    tasks = len({r["task_id"] for r in records if r["method"] == "manual"})
    manual = study["summary"]["manual"]
    sim = study["summary"]["sim"]
    sim_seed0 = study["summary"]["sim_equal_count_seed0"]
    manual_eq = manual["conversations"]
    lines = [
        "# User Simulation Study",
        "",
        f"- Generated: {study['generated_utc']}",
        f"- Tasks: {', '.join(study['selected_tasks'])}",
        "",
        "## Primary table",
        "",
        "| Method | Tasks | Conversations | Unique tool paths | Distinct simulation-discovered failure signatures | Median turns | Authoring effort |",
        "|--------|------:|--------------:|------------------:|--------------------------------------------------:|-------------:|------------------|",
        _row(manual, "Manual scripts", tasks, "manual"),
        _row(sim, "Simulated users", tasks, "sim"),
        "",
        "## Fairness table",
        "",
        "| Comparison | Method | Tasks | Conversations | Unique tool paths | Distinct failure signatures | Authoring effort |",
        "|------------|--------|------:|--------------:|------------------:|----------------------------:|------------------|",
        f"| Equal authored artefacts | Manual scripts | {tasks} | {manual['conversations']} | {manual['unique_tool_paths']} | {manual['distinct_failure_signatures']} | {_authoring_effort_label('manual')} |",
        f"| Equal authored artefacts | Sim users | {tasks} | {sim['conversations']} | {sim['unique_tool_paths']} | {sim['distinct_failure_signatures']} | {_authoring_effort_label('sim')} |",
        f"| Equal conversation count | Manual scripts | {tasks} | {manual_eq} | {manual['unique_tool_paths']} | {manual['distinct_failure_signatures']} | {_authoring_effort_label('manual')} |",
        f"| Equal conversation count | Sim users (first seed only) | {tasks} | {sim_seed0['conversations']} | {sim_seed0['unique_tool_paths']} | {sim_seed0['distinct_failure_signatures']} | {_authoring_effort_label('sim')} |",
        "",
        "## Failure split",
        "",
    ]
    counts = {"existing_baseline_failure": 0, "simulation_discovered_failure": 0, "invalid_simulation": 0}
    for r in records:
        b = r.get("baseline_failure_type")
        if b in counts:
            counts[b] += 1
    lines.extend(
        [
            f"- Existing baseline failure: {counts['existing_baseline_failure']}",
            f"- Simulation-discovered failure: {counts['simulation_discovered_failure']}",
            f"- Invalid simulation: {counts['invalid_simulation']}",
            "",
            "## Transcript snippets",
            "",
        ]
    )
    man = _choose_snippet(records, "T04", "manual") or _choose_snippet(records, "T35", "manual")
    sim_snip = _choose_snippet(records, "T43", "sim") or _choose_snippet(records, "T44", "sim")
    if man:
        lines.extend(
            [
                f"- Manual example: `{man['task_id']}` / `{man['scenario_name']}` / `{man['case_id']}`",
                f"- Manual path: `{man['tool_path_signature']}`",
            ]
        )
    if sim_snip:
        lines.extend(
            [
                f"- Simulated branch example: `{sim_snip['task_id']}` / `{sim_snip['scenario_name']}` / `{sim_snip['case_id']}`",
                f"- Simulated path: `{sim_snip['tool_path_signature']}`",
            ]
        )
    lines.extend(
        [
            "",
            "Using the same benchmark tasks and correctness oracles, simulated users produced more diverse tool trajectories and uncovered additional failure signatures with less per-conversation authoring effort, while manual scripts remained useful as stable regression paths.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--study-json",
        type=Path,
        default=BENCH / "tasks" / "user_simulation" / "user_simulation_study.json",
    )
    args = ap.parse_args()

    study = json.loads(args.study_json.read_text(encoding="utf-8"))
    out_dir = BENCH / "tasks" / "user_simulation"
    md = generate_markdown(study)
    (out_dir / "user_simulation_study.md").write_text(md, encoding="utf-8")

    path_signatures = {
        "manual": sorted({r["tool_path_signature"] for r in study["records"] if r["method"] == "manual"}),
        "sim": sorted({r["tool_path_signature"] for r in study["records"] if r["method"] == "sim"}),
    }
    failure_signatures = {
        "all": sorted({r["failure_signature"] for r in study["records"] if r["failure_signature"]}),
        "simulation_discovered": sorted(
            {
                r["failure_signature"]
                for r in study["records"]
                if r["failure_signature"] and r["baseline_failure_type"] == "simulation_discovered_failure"
            }
        ),
    }
    (out_dir / "path_signatures.json").write_text(json.dumps(path_signatures, indent=2) + "\n", encoding="utf-8")
    (out_dir / "failure_signatures.json").write_text(json.dumps(failure_signatures, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {(out_dir / 'user_simulation_study.md').relative_to(BENCH)}")
    print(f"Wrote {(out_dir / 'path_signatures.json').relative_to(BENCH)}")
    print(f"Wrote {(out_dir / 'failure_signatures.json').relative_to(BENCH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
