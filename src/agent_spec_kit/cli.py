"""CLI: ``agent-spec-kit run PATH``."""

from __future__ import annotations

import argparse
import asyncio
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from agent_spec_kit.cli_reporting import (
    emit_error,
    emit_failure_detail,
    emit_list_table,
    emit_note,
    emit_summary_table,
)
from agent_spec_kit.discovery import collect_module_paths, import_paths
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.registries import ScenarioDef, iter_scenarios, reset_registries
from agent_spec_kit.runner import JobResult, WorkerJob, run_scenario_job, worker_run_job


def _parse_csv(s: str | None) -> frozenset[str]:
    if not s:
        return frozenset()
    return frozenset(x.strip() for x in s.split(",") if x.strip())


def _scenario_matches_tags(
    sd: ScenarioDef,
    *,
    tags_any: frozenset[str],
    tags_all: frozenset[str],
) -> bool:
    st = set(sd.tags)
    if tags_any and not (st & tags_any):
        return False
    if tags_all and not tags_all <= st:
        return False
    return True


async def _run_serial(
    jobs: list[tuple[ScenarioDef, int, int, int]], *, fail_fast: bool
) -> list[JobResult]:
    out: list[JobResult] = []
    for sd, case_index, idx, total in jobs:
        r = await run_scenario_job(
            sd, case_index=case_index, repeat_index=idx, repeat_total=total
        )
        out.append(r)
        if fail_fast and not r.ok:
            break
    return out


def _build_jobs(scenarios: list[ScenarioDef]) -> list[tuple[ScenarioDef, int, int, int]]:
    """(ScenarioDef, case_index, repeat_index, repeat_total)."""
    jobs: list[tuple[ScenarioDef, int, int, int]] = []
    for sd in scenarios:
        n_cases = max(1, len(scenario_case_runs(sd)))
        total = sd.repeats
        for cix in range(n_cases):
            for k in range(total):
                jobs.append((sd, cix, k + 1, total))
    return jobs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-spec-kit")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="discover and run scenario tests")
    run_p.add_argument("path", type=Path, help="file or directory")
    run_p.add_argument("--tags", default=None, help="comma-separated tags; scenario must match any")
    run_p.add_argument(
        "--tags-all",
        default=None,
        help="comma-separated tags; scenario must contain all",
    )
    run_p.add_argument("--list", action="store_true", help="print discovered scenarios and exit")
    run_p.add_argument("--fail-fast", action="store_true", help="stop after first failure")
    run_p.add_argument("-n", type=int, default=1, help="worker processes (default: 1 serial in-process)")
    args = parser.parse_args(argv)
    if args.cmd != "run":
        return 2

    tags_any = _parse_csv(args.tags)
    tags_all = _parse_csv(args.tags_all)
    root = args.path
    if not root.exists():
        emit_error(f"path does not exist: {root}")
        return 2

    reset_registries()
    paths = collect_module_paths(root)
    if not paths:
        emit_error("no test_*.py or fixtures.py found")
        return 1 if not args.list else 0

    import_paths(paths)

    scenarios = [s for s in iter_scenarios() if _scenario_matches_tags(s, tags_any=tags_any, tags_all=tags_all)]

    if args.list:
        emit_list_table(scenarios)
        return 0

    jobs = _build_jobs(scenarios)
    if not jobs:
        print("0 passed, 0 failed (no scenarios)")
        return 0

    path_tuple = tuple(str(p) for p in paths)
    results: list[JobResult] = []

    if args.fail_fast and args.n > 1:
        emit_note("--fail-fast runs serially (-n ignored)")

    if args.n <= 1:
        results = asyncio.run(_run_serial(jobs, fail_fast=args.fail_fast))
    else:
        worker_jobs: list[WorkerJob] = []
        for sd, cix, idx, total in jobs:
            worker_jobs.append(
                WorkerJob(
                    paths=path_tuple,
                    scenario_module=sd.module,
                    scenario_name=sd.name,
                    case_index=cix,
                    repeat_index=idx,
                    repeat_total=total,
                )
            )
        with ProcessPoolExecutor(max_workers=args.n) as ex:
            futures = {ex.submit(worker_run_job, wj): wj for wj in worker_jobs}
            for fut in as_completed(futures):
                r = fut.result()
                results.append(r)
                if args.fail_fast and not r.ok:
                    ex.shutdown(wait=False, cancel_futures=True)
                    break

    for r in results:
        if not r.ok:
            emit_failure_detail(r)
    emit_summary_table(results)
    failed = sum(1 for r in results if not r.ok)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
