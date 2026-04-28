"""CLI: ``agent-spec-kit run PATH``."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

import agent_spec_kit as ask
from agent_spec_kit.cli_reporting import (
    emit_error,
    emit_failure_detail,
    emit_list_table,
    emit_note,
    emit_summary_table,
)
from agent_spec_kit.discovery import collect_module_paths, import_paths
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.result_store import LocalResultStore, write_json_blob
from agent_spec_kit.registries import ScenarioDef, iter_scenarios, reset_registries
from agent_spec_kit.runner import JobResult, WorkerJob, run_scenario_job, worker_run_job
from agent_spec_kit.storage_records import (
    AssertionResultRecord,
    RepeatResultRecord,
    RunRecord,
    ScenarioResultRecord,
    StorageConfig,
    parameter_key,
    scenario_key,
)


def _parse_csv(s: str | None) -> frozenset[str]:
    if not s:
        return frozenset()
    return frozenset(x.strip() for x in s.split(",") if x.strip())


def _parse_metadata(items: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"invalid --metadata value {item!r}; expected key=value")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"invalid --metadata value {item!r}; key cannot be empty")
        out[key] = value
    return out


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _run_id() -> str:
    ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    return f"run_{ts}_{uuid.uuid4().hex[:6]}"


def _experiment_id(name: str) -> str:
    return "exp_" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]  # noqa: S324


def _git(cmd: list[str]) -> str | None:
    try:
        cp = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError:
        return None
    if cp.returncode != 0:
        return None
    return cp.stdout.strip() or None


class GitMetadata(TypedDict):
    git_commit: str | None
    git_branch: str | None
    git_dirty: bool | None


def collect_git_metadata() -> GitMetadata:
    commit = _git(["git", "rev-parse", "HEAD"])
    branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    dirty = _git(["git", "status", "--porcelain"])
    return {
        "git_commit": commit,
        "git_branch": branch,
        "git_dirty": (bool(dirty) if dirty is not None else None),
    }


def _status_from_job_result(r: JobResult) -> str:
    return r.status if r.status in {"passed", "failed", "error", "timeout", "skipped"} else ("passed" if r.ok else "failed")


def _to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _write_repeat_blobs(
    *,
    store: LocalResultStore,
    run_id: str,
    scenario_result_id: str,
    result: JobResult,
) -> tuple[RepeatResultRecord, list[AssertionResultRecord]]:
    repeat_id = f"{scenario_result_id}_r{result.repeat_index:03d}"
    run_blob_dir = store.sqlite_path.parent / "blobs" / run_id

    events_blob = write_json_blob(
        run_blob_dir / f"repeat_{result.repeat_index:03d}_events.json.gz",
        _to_jsonable([turn.events for turn in result.turn_results]),
    )
    transcript_blob = write_json_blob(
        run_blob_dir / f"repeat_{result.repeat_index:03d}_transcript.json.gz",
        _to_jsonable(result.turn_results),
    )
    assertions_blob = write_json_blob(
        run_blob_dir / f"repeat_{result.repeat_index:03d}_assertions.json.gz",
        _to_jsonable(result.assertions),
    )
    counterexample_blob = None
    if result.counterexample is not None:
        counterexample_blob = write_json_blob(
            run_blob_dir / f"repeat_{result.repeat_index:03d}_counterexample.json.gz",
            _to_jsonable(result.counterexample),
        )
    raw_error_blob = None
    if result.raw_error:
        raw_error_blob = write_json_blob(
            run_blob_dir / f"repeat_{result.repeat_index:03d}_raw_error.json.gz",
            {"error": result.raw_error},
        )

    record = RepeatResultRecord(
        repeat_result_id=repeat_id,
        scenario_result_id=scenario_result_id,
        repeat_index=result.repeat_index,
        status=_status_from_job_result(result),  # type: ignore[arg-type]
        started_at=result.started_at or _now_iso(),
        finished_at=result.finished_at,
        duration_ms=int(result.duration_s * 1000),
        output_preview=result.output_preview,
        failure_kind=result.failure_kind,
        failure_message=result.failure_message,
        events_blob_path=events_blob,
        transcript_blob_path=transcript_blob,
        assertions_blob_path=assertions_blob,
        counterexample_blob_path=counterexample_blob,
        raw_error_blob_path=raw_error_blob,
    )
    assertions: list[AssertionResultRecord] = []
    for idx, a in enumerate(result.assertions):
        cx_blob = None
        if isinstance(a.get("counterexample"), dict):
            cx_blob = write_json_blob(
                run_blob_dir / f"repeat_{result.repeat_index:03d}_assertion_{idx + 1:03d}_counterexample.json.gz",
                _to_jsonable(a.get("counterexample")),
            )
        assertions.append(
            AssertionResultRecord(
                assertion_id=f"{repeat_id}_a{idx + 1:03d}",
                repeat_result_id=repeat_id,
                assertion_type=str(a.get("assertion_type", "assertion")),
                actor=a.get("actor"),
                turn_index=a.get("turn_index"),
                status=str(a.get("status", "passed")),  # type: ignore[arg-type]
                message=a.get("message"),
                details=_to_jsonable(a.get("details", {})),
                counterexample_blob_path=cx_blob,
            )
        )
    return record, assertions


def _aggregate_scenario_result(
    current: ScenarioResultRecord,
    repeats: list[RepeatResultRecord],
) -> ScenarioResultRecord:
    repeats_passed = sum(1 for rr in repeats if rr.status == "passed")
    repeats_failed = len(repeats) - repeats_passed
    statuses = {rr.status for rr in repeats}
    status = "passed"
    if "timeout" in statuses:
        status = "timeout"
    elif "error" in statuses:
        status = "error"
    elif "failed" in statuses:
        status = "failed"
    duration_ms = sum(rr.duration_ms or 0 for rr in repeats) if repeats else None
    return ScenarioResultRecord(
        scenario_result_id=current.scenario_result_id,
        run_id=current.run_id,
        scenario_name=current.scenario_name,
        scenario_module=current.scenario_module,
        scenario_file=current.scenario_file,
        scenario_key=current.scenario_key,
        parameter_key=current.parameter_key,
        parameters=current.parameters,
        tags=current.tags,
        status=status,  # type: ignore[arg-type]
        repeats_total=current.repeats_total,
        repeats_passed=repeats_passed,
        repeats_failed=repeats_failed,
        duration_ms=duration_ms,
        summary={
            "repeats_total": current.repeats_total,
            "repeats_passed": repeats_passed,
            "repeats_failed": repeats_failed,
            "statuses": sorted(statuses),
        },
    )


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


def _run_ui(*, host: str, port: int, open_browser: bool, serve_frontend: bool) -> int:
    try:
        import uvicorn

        from agent_spec_kit.web.server import DIST_DIR, create_app
    except ImportError as e:
        emit_error(
            "the `ui` command requires the [ui] extra. "
            "Install with: pip install 'agent-spec-kit[ui]'"
        )
        emit_note(f"  (import error: {e})")
        return 2

    if serve_frontend and not (DIST_DIR / "index.html").exists():
        emit_note(
            f"frontend bundle missing at {DIST_DIR}; serving API only. "
            "Run `npm --prefix frontend install && npm --prefix frontend run build`"
            " to build the SPA."
        )

    app = create_app(serve_frontend=serve_frontend)
    url = f"http://{host}:{port}/"
    emit_note(f"agent-spec-kit ui listening on {url}")
    if open_browser:
        import webbrowser

        webbrowser.open(url)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


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
    run_p.add_argument("--experiment", default="default", help="experiment name (default: default)")
    run_p.add_argument("--metadata", action="append", default=[], help="metadata key=value (repeatable)")
    run_p.add_argument("--notes", default=None, help="optional run notes")
    sub.add_parser("runs", help="show recent runs")
    show_p = sub.add_parser("show", help="show one run")
    show_p.add_argument("run_id", help="run id")
    ui_p = sub.add_parser("ui", help="serve the results browser (requires the [ui] extra)")
    ui_p.add_argument("--host", default="127.0.0.1")
    ui_p.add_argument("--port", type=int, default=8765)
    ui_p.add_argument(
        "--open", dest="open_browser", action="store_true", help="open the UI in your browser"
    )
    ui_p.add_argument(
        "--no-frontend",
        action="store_true",
        help="serve API only; useful when running Vite dev server separately",
    )
    args = parser.parse_args(argv)
    store = LocalResultStore(StorageConfig())
    if args.cmd == "runs":
        rows = store.list_runs(limit=20)
        for row in rows:
            print(
                f"{row['run_id']}  {row['experiment_name']:<16}  {row['status']:<7}  "
                f"{row['scenario_passed']}/{row['scenario_count']} scenarios  {row['started_at']}"
            )
        return 0
    if args.cmd == "show":
        row = store.get_run(args.run_id)
        if row is None:
            emit_error(f"run not found: {args.run_id}")
            return 1
        print(f"Experiment: {row['experiment_name']}")
        print(f"Run: {row['run_id']}")
        if row["notes"]:
            print(f"Notes: {row['notes']}")
            print("")
        summary = cast(dict[str, Any], row["summary"])
        print(f"Scenarios: {summary.get('scenario_count', 0)}")
        print(f"Passed: {summary.get('scenario_passed', 0)}")
        print(f"Failed: {summary.get('scenario_failed', 0)}")
        print(f"Repeat pass rate: {summary.get('repeat_pass_rate', 0.0):.3f}")
        failures = row["failures"]
        if failures:
            print("\nFailures:")
            shown: set[str] = set()
            for failure in failures:
                key = str(failure["scenario_key"])
                if key in shown:
                    continue
                shown.add(key)
                msg = failure["failure_message"] or "(no message)"
                print(f"- {key}\n  {msg}")
        return 0
    if args.cmd == "ui":
        return _run_ui(
            host=args.host,
            port=args.port,
            open_browser=args.open_browser,
            serve_frontend=not args.no_frontend,
        )
    if args.cmd != "run":
        return 2

    tags_any = _parse_csv(args.tags)
    tags_all = _parse_csv(args.tags_all)
    root = args.path
    if not root.exists():
        emit_error(f"path does not exist: {root}")
        return 2
    try:
        user_metadata = _parse_metadata(args.metadata)
    except ValueError as e:
        emit_error(str(e))
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

    run_id = _run_id()
    git_meta = collect_git_metadata()
    run_record = RunRecord(
        run_id=run_id,
        experiment_name=args.experiment or "default",
        experiment_id=_experiment_id(args.experiment or "default"),
        started_at=_now_iso(),
        status="passed",
        command=" ".join(["agent-spec-kit", *sys.argv[1:]]) if sys.argv else "agent-spec-kit run",
        notes=args.notes,
        metadata=user_metadata,
        git_commit=git_meta["git_commit"],
        git_branch=git_meta["git_branch"],
        git_dirty=git_meta["git_dirty"],
        python_version=platform.python_version(),
        package_version=getattr(ask, "__version__", None),
    )
    store.create_run(run_record)

    scenario_records: dict[tuple[str, int], ScenarioResultRecord] = {}
    scenario_repeats: dict[str, list[RepeatResultRecord]] = {}
    for sd in scenarios:
        runs = scenario_case_runs(sd)
        for case_index, case in enumerate(runs):
            skey = scenario_key(sd.name, case)
            pkey = parameter_key(case)
            scenario_id = f"{run_id}_{sd.module}.{sd.name}_{case_index:03d}"
            record = ScenarioResultRecord(
                scenario_result_id=scenario_id,
                run_id=run_id,
                scenario_name=sd.name,
                scenario_module=sd.module,
                scenario_file=sd.source,
                scenario_key=skey,
                parameter_key=pkey,
                parameters={k: v.id for k, v in case.items()},
                tags=sd.tags,
                status="skipped",
                repeats_total=sd.repeats,
                repeats_passed=0,
                repeats_failed=0,
                duration_ms=None,
                summary={},
            )
            scenario_records[(f"{sd.module}.{sd.name}", case_index)] = record
            scenario_repeats[record.scenario_result_id] = []
            store.save_scenario_result(record)

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
                job_key = (
                    f"{futures[fut].scenario_module}.{futures[fut].scenario_name}",
                    futures[fut].case_index,
                )
                sr = scenario_records.get(job_key)
                if sr is not None:
                    repeat_record, assertions = _write_repeat_blobs(
                        store=store,
                        run_id=run_id,
                        scenario_result_id=sr.scenario_result_id,
                        result=r,
                    )
                    store.save_repeat_result(repeat_record)
                    for assertion in assertions:
                        store.save_assertion_result(assertion)
                    scenario_repeats[sr.scenario_result_id].append(repeat_record)
                if args.fail_fast and not r.ok:
                    ex.shutdown(wait=False, cancel_futures=True)
                    break
    if args.n <= 1:
        for (sd, cix, _idx, _total), r in zip(jobs, results, strict=False):
            job_key = (f"{sd.module}.{sd.name}", cix)
            sr = scenario_records.get(job_key)
            if sr is None:
                continue
            repeat_record, assertions = _write_repeat_blobs(
                store=store,
                run_id=run_id,
                scenario_result_id=sr.scenario_result_id,
                result=r,
            )
            store.save_repeat_result(repeat_record)
            for assertion in assertions:
                store.save_assertion_result(assertion)
            scenario_repeats[sr.scenario_result_id].append(repeat_record)

    for sr in scenario_records.values():
        repeats = scenario_repeats[sr.scenario_result_id]
        final_sr = _aggregate_scenario_result(sr, repeats)
        store.save_scenario_result(final_sr)

    for r in results:
        if not r.ok:
            emit_failure_detail(r)
    emit_summary_table(results)
    summary = store.compute_run_summary(run_id)
    store.finish_run(run_id, summary)
    failed = sum(1 for r in results if not r.ok)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
