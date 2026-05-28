#!/usr/bin/env python3
"""Run manual-vs-sim telecom user simulation study."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from user_simulation_lib import (
    BENCH,
    append_jsonl,
    discover_user_sim_scenarios,
    load_study_config,
    record_from_job,
    write_transcript,
)
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.runner import run_scenario_job


def _task_from_tags(tags: tuple[str, ...]) -> str | None:
    for t in tags:
        if t.startswith("task:"):
            return t.split(":", 1)[1]
    return None


def _is_method(tags: tuple[str, ...], method: str) -> bool:
    return f"method:{method}" in tags


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "conversations": len(records),
        "unique_tool_paths": len({r["tool_path_signature"] for r in records}),
        "unique_tool_sets": len({tuple(r["tool_set"]) for r in records}),
        "unique_tool_bigrams": len({b for r in records for b in r["tool_bigram_set"]}),
        "distinct_failure_signatures": len({r["failure_signature"] for r in records if r["failure_signature"]}),
        "distinct_simulation_discovered_failure_signatures": len(
            {
                r["failure_signature"]
                for r in records
                if r["failure_signature"] and r["baseline_failure_type"] == "simulation_discovered_failure"
            }
        ),
        "median_turns": median([r["turn_count"] for r in records]) if records else 0,
    }


async def _run(args: argparse.Namespace) -> int:
    cfg = load_study_config()
    selected_tasks = list(cfg["primary_tasks"])
    if args.include_interesting:
        selected_tasks.extend(cfg.get("interesting_tasks", []))
    selected_set = set(selected_tasks)

    scenarios = discover_user_sim_scenarios()
    manual_defs = []
    sim_defs = []
    for sdef in scenarios:
        task = _task_from_tags(sdef.tags)
        if task not in selected_set:
            continue
        if _is_method(sdef.tags, "manual"):
            manual_defs.append((task, sdef))
        elif _is_method(sdef.tags, "sim"):
            sim_defs.append((task, sdef))

    records: list[dict[str, Any]] = []
    out_dir = BENCH / "tasks" / "user_simulation"
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runs_root = out_dir / "transcripts"
    run_dir = runs_root / run_id
    traces_dir = run_dir / "agent_traces"
    logs_dir = run_dir / "logs"
    transcripts_dir = run_dir / "cases"
    logs_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TELCO_AGENT_TRACE_DIR"] = str(traces_dir)
    run_log_path = logs_dir / "run.log"
    run_events_path = logs_dir / "run_events.jsonl"
    run_log = run_log_path.open("w", encoding="utf-8")

    def _log(msg: str) -> None:
        print(msg, flush=True)
        run_log.write(msg + "\n")
        run_log.flush()

    append_jsonl(
        run_events_path,
        {
            "kind": "run_start",
            "ts": datetime.now(UTC).isoformat(),
            "run_id": run_id,
            "workers": args.workers,
            "selected_tasks": selected_tasks,
        },
    )

    async def _run_one(task: str, method: str, sdef, case_index: int):
        case_total = len(scenario_case_runs(sdef))
        _log(
            f"[user-sim] start task={task} method={method} "
            f"scenario={sdef.name} case={case_index + 1}/{case_total}",
        )
        append_jsonl(
            run_events_path,
            {
                "kind": "case_start",
                "ts": datetime.now(UTC).isoformat(),
                "task_id": task,
                "method": method,
                "scenario_name": sdef.name,
                "case_index": case_index,
                "case_total": case_total,
            },
        )
        job = await run_scenario_job(
            sdef,
            case_index=case_index,
            repeat_index=1,
            repeat_total=1,
        )
        _log(
            f"[user-sim] done  task={task} method={method} "
            f"scenario={sdef.name} case_id={job.case_id} status={job.status} ok={job.ok}",
        )
        append_jsonl(
            run_events_path,
            {
                "kind": "case_done",
                "ts": datetime.now(UTC).isoformat(),
                "task_id": task,
                "method": method,
                "scenario_name": sdef.name,
                "case_id": job.case_id,
                "status": job.status,
                "ok": job.ok,
                "detail": job.detail,
                "duration_s": job.duration_s,
            },
        )
        return task, method, job

    work_items: list[tuple[str, str, Any, int]] = []
    for task, sdef in sorted(manual_defs):
        for idx in range(len(scenario_case_runs(sdef))):
            work_items.append((task, "manual", sdef, idx))
    for task, sdef in sorted(sim_defs):
        for idx in range(len(scenario_case_runs(sdef))):
            work_items.append((task, "sim", sdef, idx))

    sem = asyncio.Semaphore(max(1, args.workers))

    async def _bounded(task: str, method: str, sdef, idx: int):
        async with sem:
            return await _run_one(task, method, sdef, idx)

    total = len(work_items)
    _log(
        f"[user-sim] running {total} scenario case jobs with -n {args.workers}",
    )
    completed = 0
    for fut in asyncio.as_completed([_bounded(*item) for item in work_items]):
        task, method, job = await fut
        rec = record_from_job(task, method, job)
        records.append(rec)
        write_transcript(transcripts_dir / f"{task}_{method}_{job.case_id}.json", job)
        completed += 1
        _log(f"[user-sim] progress {completed}/{total}")

    study = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "run_dir": str(run_dir.relative_to(BENCH)),
        "run_log_path": str(run_log_path.relative_to(BENCH)),
        "run_events_path": str(run_events_path.relative_to(BENCH)),
        "agent_trace_dir": str(traces_dir.relative_to(BENCH)),
        "selected_tasks": selected_tasks,
        "records": records,
        "summary": {
            "manual": _aggregate([r for r in records if r["method"] == "manual"]),
            "sim": _aggregate([r for r in records if r["method"] == "sim"]),
            "sim_equal_count_seed0": _aggregate([r for r in records if r["method"] == "sim" and r["seed"] == 0]),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "user_simulation_study.json").write_text(
        json.dumps(study, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps(study, indent=2) + "\n",
        encoding="utf-8",
    )
    append_jsonl(
        run_events_path,
        {
            "kind": "run_done",
            "ts": datetime.now(UTC).isoformat(),
            "run_id": run_id,
            "record_count": len(records),
            "run_manifest": str((run_dir / "run_manifest.json").relative_to(BENCH)),
        },
    )
    run_log.write(f"[user-sim] wrote run_manifest={run_dir / 'run_manifest.json'}\n")
    run_log.close()
    print(f"Wrote {(out_dir / 'user_simulation_study.json').relative_to(BENCH)}")
    print(f"Wrote {(run_dir / 'run_manifest.json').relative_to(BENCH)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-interesting", action="store_true", help="Include optional T03/T44 tasks.")
    ap.add_argument("-n", "--workers", type=int, default=12, help="Parallel workers (default: 12).")
    args = ap.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
