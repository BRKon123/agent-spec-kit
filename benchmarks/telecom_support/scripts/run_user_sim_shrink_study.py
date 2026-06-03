#!/usr/bin/env python3
"""User-simulation shrink + regression extraction study runner."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.runner import run_scenario_job
from user_sim_shrink_study_lib import (
    BENCH,
    CONFIG_PATH,
    capture_candidate,
    classify_stability,
    discover_sim_scenarios,
    extract_one_candidate,
    find_case_index,
    load_results,
    load_shrink_study_config,
    merge_summary,
    record_from_job,
    save_results,
    shrink_one_candidate,
    select_for_shrink_from_extraction,
    build_shrink_config,
    stratified_pick,
    write_transcript,
)

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

_LOG_FILE: Path | None = None


def _log(msg: str) -> None:
    line = f"[{datetime.now(UTC).strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if _LOG_FILE is not None:
        with _LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def _results_path(cfg: dict) -> Path:
    return BENCH / cfg["outputs"]["results_json"]


def bootstrap_sim_records(cfg: dict, study_path: Path) -> tuple[list[dict], str]:
    """Load sim records + transcript paths from a prior user_simulation_study.json."""
    study = json.loads(study_path.read_text(encoding="utf-8"))
    primary = set(cfg["primary_tasks"])
    run_dir = BENCH / study.get("run_dir", "")
    records: list[dict] = []
    scenarios = {t: s for t, s in discover_sim_scenarios(cfg)}
    for rec in study.get("records") or []:
        if rec.get("method") != "sim" or rec.get("task_id") not in primary:
            continue
        task = rec["task_id"]
        sdef = scenarios.get(task)
        if sdef is None:
            continue
        case_index = find_case_index(sdef, rec.get("case_id", ""))
        if case_index is None:
            continue
        tpath = run_dir / "cases" / f"{task}_sim_{rec['case_id']}.json"
        if not tpath.exists():
            continue
        rec = dict(rec)
        rec["transcript_path"] = str(tpath.relative_to(BENCH))
        rec["case_index"] = case_index
        records.append(rec)
    return records, study.get("run_id", "bootstrap")


async def phase_sim(cfg: dict, args: argparse.Namespace, results: dict) -> None:
    scenarios = discover_sim_scenarios(cfg)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    transcripts_dir = BENCH / "tasks" / "user_simulation" / "transcripts" / run_id / "cases"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    traces_dir = BENCH / "tasks" / "user_simulation" / "transcripts" / run_id / "agent_traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TELCO_AGENT_TRACE_DIR"] = str(traces_dir)
    records: list[dict] = []
    sem = asyncio.Semaphore(max(1, args.workers))

    async def _one(task: str, sdef, idx: int):
        async with sem:
            job = await run_scenario_job(sdef, case_index=idx, repeat_index=1, repeat_total=1)
            rec = record_from_job(task, "sim", job)
            path = transcripts_dir / f"{task}_sim_{job.case_id}.json"
            write_transcript(path, job)
            rec["transcript_path"] = str(path.relative_to(BENCH))
            rec["case_index"] = idx
            return rec

    work = []
    for task, sdef in scenarios:
        for idx in range(len(scenario_case_runs(sdef))):
            work.append(_one(task, sdef, idx))
    print(f"[shrink-study] sim phase: {len(work)} jobs, workers={args.workers}")
    for fut in asyncio.as_completed(work):
        records.append(await fut)
    results["sim_run_id"] = run_id
    results["sim_records"] = records
    results["transcripts_dir"] = str(transcripts_dir.relative_to(BENCH))
    print(f"[shrink-study] sim done: {len(records)} records")


async def phase_collect(cfg: dict, results: dict, workers: int = 4) -> None:
    scenarios = {t: s for t, s in discover_sim_scenarios(cfg)}
    failing = [r for r in results.get("sim_records") or [] if r.get("failure_signature")]
    sem = asyncio.Semaphore(max(1, workers))
    candidates: list[dict] = []

    async def _one(rec: dict) -> dict | None:
        task = rec["task_id"]
        sdef = scenarios.get(task)
        if sdef is None:
            return None
        case_index = rec.get("case_index")
        if case_index is None:
            case_index = find_case_index(sdef, rec.get("case_id", ""))
        if case_index is None:
            return None
        tpath = BENCH / rec["transcript_path"]
        async with sem:
            return await capture_candidate(
                sdef,
                task_id=task,
                case_index=int(case_index),
                transcript_path=tpath,
                record=rec,
            )

    parts = await asyncio.gather(*[_one(r) for r in failing])
    for cap in parts:
        if cap:
            candidates.append(cap)
    results["candidates"] = candidates
    ok_n = sum(1 for c in candidates if c.get("capture_status") == "ok")
    _log(f"collect done: {len(candidates)} candidates ({ok_n} captured ok)")


async def phase_stability(cfg: dict, results: dict, workers: int = 4) -> None:
    from agent_spec_kit.generative import FailureSignature

    scenarios = {t: s for t, s in discover_sim_scenarios(cfg)}
    confirm = int(cfg.get("confirm_runs", 2))
    cap_pool = int(cfg["caps"]["max_stable_pool"])
    counts = {"stable": 0, "flaky": 0, "non_reproducing": 0, "capture_failed": 0}
    sem = asyncio.Semaphore(max(1, workers))

    async def _one(cand: dict) -> str:
        if cand.get("capture_status") != "ok":
            cand["stability"] = "capture_failed"
            return "capture_failed"
        sdef = scenarios[cand["task_id"]]
        sig = FailureSignature.from_dict(cand["failure_signature"])
        captured = {int(k): tuple(v) for k, v in cand["captured_per_step"].items()}
        async with sem:
            status = await classify_stability(
                sdef,
                case_index=int(cand["case_index"]),
                captured_per_step=captured,
                failing_step_index=int(cand["failing_step_index"]),
                target_sig=sig,
                confirm_runs=confirm,
            )
        cand["stability"] = status
        return status

    for status in await asyncio.gather(*[_one(c) for c in results.get("candidates") or []]):
        counts[status] = counts.get(status, 0) + 1
    stable_selected = 0
    for cand in sorted(
        results.get("candidates") or [],
        key=lambda c: (c.get("task_id", ""), c.get("persona_seed", 0)),
    ):
        if cand.get("stability") == "stable" and stable_selected < cap_pool:
            cand["selected_for_shrink"] = True
            stable_selected += 1
        else:
            cand["selected_for_shrink"] = False
    results["stability_counts"] = counts
    _log(f"stability done: {counts}, selected_for_shrink={stable_selected}")


async def phase_shrink(
    cfg: dict,
    results: dict,
    *,
    checkpoint_path: Path | None = None,
    workers: int = 4,
) -> None:
    scenarios = {t: s for t, s in discover_sim_scenarios(cfg)}
    shrink_cfg = build_shrink_config(cfg)
    max_shrink = int(cfg["caps"]["max_to_shrink"])
    to_process = [
        c
        for c in results.get("candidates") or []
        if c.get("selected_for_shrink")
    ][:max_shrink]
    total = len(to_process)
    sem = asyncio.Semaphore(max(1, workers))
    ckpt_lock = asyncio.Lock()
    done = 0

    async def _one(cand: dict, i: int) -> None:
        nonlocal done
        if cand.get("shrink", {}).get("shrink_status") == "ok":
            _log(f"shrink [{i}/{total}] {cand['id']}: skip (already ok)")
            cand["selected_for_extract"] = True
            return
        _log(
            f"shrink [{i}/{total}] {cand['id']} "
            f"({cand['task_id']} seed{cand.get('persona_seed')}) starting..."
        )
        sdef = scenarios[cand["task_id"]]
        async with sem:
            cand["shrink"] = await shrink_one_candidate(sdef, cand, shrink_cfg)
        sh = cand["shrink"]
        cand["selected_for_extract"] = sh.get("shrink_status") == "ok"
        _log(
            f"shrink [{i}/{total}] {cand['id']}: {sh.get('shrink_status')} "
            f"turns {sh.get('original_turns')}→{sh.get('shrunk_turns')} "
            f"({sh.get('turn_reduction_pct', 0)}%) in {sh.get('shrink_time_s', '?')}s"
        )
        async with ckpt_lock:
            done += 1
            if checkpoint_path is not None:
                results["summary"] = merge_summary(results)
                save_results(checkpoint_path, results)

    await asyncio.gather(*[_one(c, i) for i, c in enumerate(to_process, start=1)])
    _log(f"shrink done: processed {done}/{total} (workers={workers})")


async def phase_extract(
    cfg: dict,
    results: dict,
    *,
    checkpoint_path: Path | None = None,
    workers: int = 4,
) -> None:
    scenarios = {t: s for t, s in discover_sim_scenarios(cfg)}
    max_ext = int(cfg["caps"]["max_to_extract"])
    pool = [
        c
        for c in results.get("candidates") or []
        if c.get("selected_for_extract") and c.get("shrink", {}).get("shrink_status") == "ok"
    ]
    picked = stratified_pick(
        pool,
        max_ext,
        key_fn=lambda c: f"{c['task_id']}:{(c.get('failure_signature') or {}).get('check_kind', '')}",
    )
    total = len(picked)
    sem = asyncio.Semaphore(max(1, workers))
    ckpt_lock = asyncio.Lock()

    async def _one(cand: dict, i: int) -> None:
        if cand.get("extraction", {}).get("file_generated"):
            _log(f"extract [{i}/{total}] {cand['id']}: skip (already extracted)")
            return
        _log(f"extract [{i}/{total}] {cand['id']} starting...")
        sdef = scenarios[cand["task_id"]]
        async with sem:
            cand["extraction"] = await extract_one_candidate(
                sdef, cand, cand.get("shrink", {}), cfg
            )
        ex = cand["extraction"]
        _log(
            f"extract [{i}/{total}] {cand['id']}: status={ex.get('extraction_status')} "
            f"file={ex.get('file_generated')} reproduces={ex.get('reproduces_failure')}"
        )
        async with ckpt_lock:
            if checkpoint_path is not None:
                results["summary"] = merge_summary(results)
                save_results(checkpoint_path, results)

    await asyncio.gather(*[_one(c, i) for i, c in enumerate(picked, start=1)])
    _log(f"extract done: {total} regressions (workers={workers})")


async def phase_rerun(cfg: dict, results: dict) -> None:
    from agent_spec_kit.discovery import collect_module_paths, import_paths
    from agent_spec_kit.registries import iter_scenarios, reset_registries

    reset_registries()
    reg_dir = BENCH / "tasks" / "regressions"
    import_paths(collect_module_paths(reg_dir))
    n = 0
    for cand in results.get("candidates") or []:
        ext = cand.get("extraction") or {}
        fn = ext.get("function_name")
        if not fn:
            continue
        for sdef in iter_scenarios():
            if sdef.name != fn and fn not in sdef.name:
                continue
            job = await run_scenario_job(sdef, case_index=0, repeat_index=1, repeat_total=1)
            ext["rerun_ok"] = job.ok
            ext["rerun_status"] = job.status
            n += 1
            _log(f"rerun [{n}] {fn}: status={job.status} ok={job.ok}")
            break
    _log(f"rerun done: {n} regression jobs")


async def _run(args: argparse.Namespace) -> int:
    global _LOG_FILE
    cfg = load_shrink_study_config()
    path = _results_path(cfg)
    log_dir = BENCH / "tasks" / "shrinking" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = log_dir / f"run_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.log"
    _log(f"study log file: {_LOG_FILE.relative_to(BENCH)}")
    _log(f"phases={args.phase} resume={args.resume} workers={args.workers}")
    results = load_results(path) if args.resume else {"generated_utc": datetime.now(UTC).isoformat()}
    if args.phase == "all":
        phases = ["sim", "collect", "stability", "shrink", "extract", "rerun"]
    else:
        phases = [p.strip() for p in args.phase.split(",") if p.strip()]
    if args.bootstrap_study and not results.get("sim_records"):
        bpath = Path(args.bootstrap_study)
        if not bpath.is_absolute():
            bpath = BENCH / bpath
        records, run_id = bootstrap_sim_records(cfg, bpath)
        results["sim_run_id"] = f"bootstrap:{run_id}"
        results["sim_records"] = records
        study = json.loads(bpath.read_text(encoding="utf-8"))
        results["transcripts_dir"] = study.get("run_dir", "")
        _log(f"bootstrap sim: {len(records)} records")
    if "sim" in phases and not args.bootstrap_study:
        await phase_sim(cfg, args, results)
    if "collect" in phases:
        if not results.get("sim_records"):
            raise SystemExit("collect requires sim_records; run --phase sim or --bootstrap-study")
        await phase_collect(cfg, results, workers=args.workers)
    if "stability" in phases:
        await phase_stability(cfg, results, workers=args.workers)
    if args.extraction_results:
        ext_path = Path(args.extraction_results)
        if not ext_path.is_absolute():
            ext_path = BENCH / ext_path
        n = select_for_shrink_from_extraction(
            results,
            ext_path,
            limit=int(cfg["caps"]["max_to_shrink"]),
        )
        for cand in results.get("candidates") or []:
            if cand.get("selected_for_shrink") and (cand.get("shrink") or {}).get(
                "shrink_status"
            ) != "ok":
                cand.pop("shrink", None)
        _log(f"shrink selection from extraction: {n} candidates (reproduces_failure)")
    if "shrink" in phases:
        _log("phase shrink starting")
        await phase_shrink(cfg, results, checkpoint_path=path, workers=args.workers)
    if "extract" in phases:
        _log("phase extract starting")
        await phase_extract(cfg, results, checkpoint_path=path, workers=args.workers)
    if "rerun" in phases:
        await phase_rerun(cfg, results)
    results["summary"] = merge_summary(results)
    save_results(path, results)
    _log(f"saved results: {path.relative_to(BENCH)}")
    if args.phase in ("all", "report") or "report" in phases:
        _log("generating markdown reports")
        from generate_user_sim_shrink_reports import main as gen_reports

        gen_reports()
        _log("reports written")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="User-sim shrink + regression study")
    p.add_argument("--phase", default="all", help="sim|collect|stability|shrink|extract|rerun|report|all")
    p.add_argument("-n", "--workers", type=int, default=6)
    p.add_argument("--resume", action="store_true", help="Load existing results JSON")
    p.add_argument(
        "--bootstrap-study",
        type=str,
        default=None,
        help="Path to user_simulation_study.json (skip sim phase, reuse transcripts)",
    )
    p.add_argument(
        "--extraction-results",
        type=str,
        default=None,
        help="Select shrink pool from extraction JSON (reproduces_failure=true)",
    )
    args = p.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
