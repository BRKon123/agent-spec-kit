#!/usr/bin/env python3
"""User-simulation extraction-only study runner (no shrinking)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from user_sim_extraction_study_lib import (
    BENCH,
    bootstrap_sim_records,
    capture_candidate,
    discover_extracted_scenario,
    discover_sim_scenarios,
    extract_failure,
    extraction_summary,
    find_case_index,
    invalidate_extracted_scenario_cache,
    load_candidates_from_shrink_json,
    load_extraction_study_config,
    load_results,
    save_results,
    validate_extraction_rerun,
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


async def phase_collect(
    cfg: dict,
    results: dict,
    *,
    workers: int,
    reuse_candidates_path: Path | None,
) -> None:
    if reuse_candidates_path is not None:
        loaded = load_candidates_from_shrink_json(reuse_candidates_path)
        if loaded:
            results["candidates"] = loaded
            _log(f"collect: reused {len(loaded)} candidates from {reuse_candidates_path.name}")
            return
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
    _log(f"collect done: {len(candidates)} candidates ({ok_n} capture ok)")


async def phase_extract(
    cfg: dict,
    results: dict,
    *,
    checkpoint_path: Path,
    workers: int,
) -> None:
    scenarios = {t: s for t, s in discover_sim_scenarios(cfg)}
    pool = [c for c in results.get("candidates") or [] if c.get("capture_status") == "ok"]
    total = len(pool)
    done = 0
    for i, cand in enumerate(pool, start=1):
        prev = cand.get("extraction") or {}
        prev_status = prev.get("extraction_status")
        if (
            prev_status in ("written", "partial", "skipped_duplicate")
            and prev.get("extraction_format") == "ast_concrete"
        ):
            _log(f"extract [{i}/{total}] {cand.get('id', '?')}: skip ({prev_status})")
            if not cand.get("extraction", {}).get("collected") and cand.get("extraction", {}).get(
                "function_name"
            ):
                fn = cand["extraction"]["function_name"]
                cand["extraction"]["collected"] = discover_extracted_scenario(str(fn)) is not None
            done += 1
            continue
        _log(f"extract [{i}/{total}] {cand.get('id', '?')} starting...")
        sdef = scenarios[cand["task_id"]]
        cand["extraction"] = await extract_failure(sdef, cand, cfg)
        ex = cand["extraction"]
        _log(
            f"extract [{i}/{total}] {cand.get('id')}: status={ex.get('extraction_status')} "
            f"file={ex.get('file_generated')} imports={ex.get('imports_ok')} "
            f"collected={ex.get('collected')}"
        )
        done += 1
        results["summary"] = extraction_summary(results)
        save_results(checkpoint_path, results)
    _log(f"extract done: {done}/{total} (sequential; append-safe)")


async def phase_rerun(
    cfg: dict,
    results: dict,
    *,
    checkpoint_path: Path,
    workers: int,
) -> None:
    from user_sim_extraction_study_lib import load_registry_for_extracted_rerun

    load_registry_for_extracted_rerun()
    pool = [
        c
        for c in results.get("candidates") or []
        if c.get("extraction", {}).get("file_generated")
    ]
    total = len(pool)
    sem = asyncio.Semaphore(max(1, workers))
    ckpt_lock = asyncio.Lock()
    done = 0

    async def _one(cand: dict, i: int) -> None:
        nonlocal done
        ex = cand.get("extraction") or {}
        if ex.get("rerun_status") in ("passed", "failed"):
            _log(f"rerun [{i}/{total}] {cand.get('id')}: skip (already validated)")
            return
        _log(f"rerun [{i}/{total}] {cand.get('id')} validating...")
        async with sem:
            cand["extraction"] = await validate_extraction_rerun(ex, cand)
        ex = cand["extraction"]
        _log(
            f"rerun [{i}/{total}] {cand.get('id')}: reproduces={ex.get('reproduces_failure')} "
            f"status={ex.get('rerun_status')} ok={ex.get('rerun_ok')}"
        )
        async with ckpt_lock:
            done += 1
            results["summary"] = extraction_summary(results)
            save_results(checkpoint_path, results)

    await asyncio.gather(*[_one(c, i) for i, c in enumerate(pool, start=1)])
    _log(f"rerun done: {done}/{total} validated (workers={workers})")


async def _run(args: argparse.Namespace) -> int:
    global _LOG_FILE
    cfg = load_extraction_study_config()
    path = _results_path(cfg)
    log_dir = BENCH / cfg["outputs"].get("logs_dir", "tasks/extraction/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = log_dir / f"run_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.log"
    _log(f"study log: {_LOG_FILE.relative_to(BENCH)}")
    _log(f"phases={args.phase} resume={args.resume} workers={args.workers}")

    results = load_results(path) if args.resume else {"generated_utc": datetime.now(UTC).isoformat()}

    if args.phase == "all":
        phases = ["collect", "extract", "rerun", "report"]
    else:
        phases = [p.strip() for p in args.phase.split(",") if p.strip()]

    reuse_path: Path | None = None
    if args.reuse_candidates:
        reuse_path = Path(args.reuse_candidates)
        if not reuse_path.is_absolute():
            reuse_path = BENCH / reuse_path

    if args.bootstrap_study:
        bpath = Path(args.bootstrap_study)
        if not bpath.is_absolute():
            bpath = BENCH / bpath
        if not results.get("sim_records"):
            records, run_id = bootstrap_sim_records(cfg, bpath)
            results["sim_run_id"] = f"bootstrap:{run_id}"
            results["sim_records"] = records
            _log(f"bootstrap: {len(records)} sim records")

    if "collect" in phases:
        if not results.get("sim_records") and not reuse_path:
            raise SystemExit("collect needs --bootstrap-study or --reuse-candidates")
        await phase_collect(cfg, results, workers=args.workers, reuse_candidates_path=reuse_path)

    if "extract" in phases:
        await phase_extract(cfg, results, checkpoint_path=path, workers=args.workers)

    if "rerun" in phases:
        await phase_rerun(cfg, results, checkpoint_path=path, workers=args.workers)

    results["summary"] = extraction_summary(results)
    save_results(path, results)
    _log(f"saved {path.relative_to(BENCH)}")

    if "report" in phases:
        from generate_user_sim_extraction_report import main as gen_report

        gen_report()
        _log("report written")

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="User-sim extraction-only study")
    p.add_argument("--phase", default="all", help="collect|extract|rerun|report|all")
    p.add_argument("-n", "--workers", type=int, default=12)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--bootstrap-study", type=str, default=None)
    p.add_argument(
        "--reuse-candidates",
        type=str,
        default=None,
        help="Reuse candidates from shrink study JSON (skip re-capture)",
    )
    args = p.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
