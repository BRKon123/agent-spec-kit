#!/usr/bin/env python3
"""Run manual / user-simulation / fuzzing telecom study (224 conversation records)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

BENCH_RUN = Path(__file__).resolve().parents[1]
REPO_RUN = BENCH_RUN.parents[1]
if str(REPO_RUN) not in sys.path:
    sys.path.insert(0, str(REPO_RUN))
if str(BENCH_RUN) not in sys.path:
    sys.path.insert(0, str(BENCH_RUN))

from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.runner import run_scenario_job
from fuzzing_study_lib import (
    BENCH,
    UiStudyRunLogger,
    append_jsonl,
    discover_fuzz_study_scenarios,
    load_study_config,
    record_from_fuzz_job,
    write_transcript,
)


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
        "distinct_failure_signatures": len(
            {r["failure_signature"] for r in records if r["failure_signature"]}
        ),
        "distinct_fuzz_discovered_failure_signatures": len(
            {
                r["failure_signature"]
                for r in records
                if r["failure_signature"] and r["baseline_failure_type"] == "fuzz_discovered_failure"
            }
        ),
        "median_turns": median([r["turn_count"] for r in records]) if records else 0,
    }


def _records_from_job(
    task: str,
    method: str,
    job: Any,
    *,
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    if method != "fuzz" or not job.fuzz_trials:
        return [record_from_fuzz_job(task, method, job, cfg=cfg)]
    out: list[dict[str, Any]] = []
    for ft in job.fuzz_trials:
        rec = record_from_fuzz_job(task, method, job, cfg=cfg)
        rec["framework_trial_index"] = int(ft.get("trial_index", 0))
        rec["mutated_user_messages"] = list(ft.get("user_turns") or rec["mutated_user_messages"])
        rec["per_step_user_turns"] = list(ft.get("per_step_user_turns") or [])
        rec["trial_status"] = ft.get("status")
        out.append(rec)
    return out


async def _run(args: argparse.Namespace) -> int:
    cfg = load_study_config()
    selected_tasks = list(cfg["primary_tasks"])
    selected_set = set(selected_tasks)

    scenarios = discover_fuzz_study_scenarios()
    manual_defs: list[tuple[str, Any]] = []
    sim_defs: list[tuple[str, Any]] = []
    fuzz_defs: list[tuple[str, Any]] = []
    for sdef in scenarios:
        task = _task_from_tags(sdef.tags)
        if task not in selected_set:
            continue
        if _is_method(sdef.tags, "manual"):
            manual_defs.append((task, sdef))
        elif _is_method(sdef.tags, "sim"):
            sim_defs.append((task, sdef))
        elif _is_method(sdef.tags, "fuzz"):
            fuzz_defs.append((task, sdef))

    records: list[dict[str, Any]] = []
    ui_run_id: str | None = None
    out_dir = BENCH / "tasks" / "fuzzing"
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runs_root = out_dir / "transcripts"
    run_dir = runs_root / run_id
    traces_dir = run_dir / "agent_traces"
    logs_dir = run_dir / "logs"
    transcripts_dir = run_dir / "cases"
    logs_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    os.environ.pop("TELCO_ENABLE_CALIBRATION_STEERING", None)
    os.environ["TELCO_DISABLE_CALIBRATION_STEERING"] = "1"
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
            "calibration_steering": False,
        },
    )

    async def _run_one(task: str, method: str, sdef, case_index: int):
        case_total = len(scenario_case_runs(sdef))
        _log(
            f"[fuzz-study] start task={task} method={method} "
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
            },
        )
        job = await run_scenario_job(
            sdef,
            case_index=case_index,
            repeat_index=1,
            repeat_total=1,
        )
        _log(
            f"[fuzz-study] done  task={task} method={method} "
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
            },
        )
        return task, method, sdef, case_index, job

    work_items: list[tuple[str, str, Any, int]] = []
    for task, sdef in sorted(manual_defs):
        for idx in range(len(scenario_case_runs(sdef))):
            work_items.append((task, "manual", sdef, idx))
    for task, sdef in sorted(sim_defs):
        for idx in range(len(scenario_case_runs(sdef))):
            work_items.append((task, "sim", sdef, idx))
    for task, sdef in sorted(fuzz_defs):
        for idx in range(len(scenario_case_runs(sdef))):
            work_items.append((task, "fuzz", sdef, idx))

    ui_logger: UiStudyRunLogger | None = None
    if not args.no_ui:
        ui_logger = UiStudyRunLogger(
            experiment=args.experiment,
            notes=args.notes or f"Fuzzing study tasks: {', '.join(selected_tasks)}",
            study_run_id=run_id,
            command="benchmarks/telecom_support/scripts/run_fuzzing_study.py",
        )
        for _task, _method, sdef, idx in work_items:
            ui_logger.register(sdef, idx)

    sem = asyncio.Semaphore(max(1, args.workers))

    async def _bounded(task: str, method: str, sdef, idx: int):
        async with sem:
            return await _run_one(task, method, sdef, idx)

    total_jobs = len(work_items)
    _log(f"[fuzz-study] running {total_jobs} scenario case jobs with -n {args.workers}")
    completed = 0
    for fut in asyncio.as_completed([_bounded(*item) for item in work_items]):
        task, method, sdef, case_index, job = await fut
        recs = _records_from_job(task, method, job, cfg=cfg)
        records.extend(recs)
        write_transcript(
            transcripts_dir / f"{task}_{method}_{job.case_id}.json",
            job,
        )
        if ui_logger is not None:
            ui_logger.persist_job(sdef, case_index, job)
        completed += 1
        _log(f"[fuzz-study] progress jobs={completed}/{total_jobs} records={len(records)}")

    if ui_logger is not None:
        ui_run_id = ui_logger.finish()
        _log(
            f"[fuzz-study] UI run logged: {ui_run_id} "
            f"(open: uv run agent-spec-kit ui → experiment {args.experiment})",
        )

    study = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "ui_run_id": ui_run_id,
        "ui_experiment": args.experiment if not args.no_ui else None,
        "run_dir": str(run_dir.relative_to(BENCH)),
        "calibration_steering": False,
        "selected_tasks": selected_tasks,
        "records": records,
        "summary": {
            "manual": _aggregate([r for r in records if r["method"] == "manual"]),
            "sim": _aggregate([r for r in records if r["method"] == "sim"]),
            "fuzz": _aggregate([r for r in records if r["method"] == "fuzz"]),
            "sim_equal_count_seed0": _aggregate(
                [r for r in records if r["method"] == "sim" and r.get("seed") == 0]
            ),
            "fuzz_equal_count_trial0": _aggregate(
                [
                    r
                    for r in records
                    if r["method"] == "fuzz" and r.get("framework_trial_index", 0) == 0
                ]
            ),
            "job_count": total_jobs,
            "record_count": len(records),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "fuzzing_runs.json").write_text(
        json.dumps(study, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps(study, indent=2) + "\n",
        encoding="utf-8",
    )
    run_log.close()
    print(f"Wrote {(out_dir / 'fuzzing_runs.json').relative_to(BENCH)} ({len(records)} records)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--workers", type=int, default=8, help="Parallel workers (default: 8).")
    ap.add_argument(
        "--experiment",
        default="fuzzing-study",
        help="UI experiment name (default: fuzzing-study).",
    )
    ap.add_argument("--notes", default=None, help="Optional notes on the UI run record.")
    ap.add_argument("--no-ui", action="store_true", help="Skip .agent_spec_kit/ UI logging.")
    args = ap.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
