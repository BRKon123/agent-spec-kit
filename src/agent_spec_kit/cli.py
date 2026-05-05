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
import time
import uuid
from concurrent.futures import Executor, Future, ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any, TypedDict, cast

import agent_spec_kit as ask
from agent_spec_kit.cli_reporting import (
    emit_error,
    emit_failure_detail,
    emit_job_compact,
    emit_list_table,
    emit_note,
    emit_summary_table,
    emit_trial_failure_detail,
)
from agent_spec_kit.discovery import collect_module_paths, import_paths
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.result_store import LocalResultStore, write_json_blob
from agent_spec_kit.registries import ScenarioDef, find_scenario, iter_scenarios, reset_registries
from agent_spec_kit.runner import (
    JobResult,
    ScenarioRepeatJob,
    _scenario_body_may_use_generative_orchestrator,
    worker_run_full_repeat_job,
)
from agent_spec_kit.storage_records import (
    AssertionResultRecord,
    FuzzTrialRecord,
    PhaseErrorRecord,
    RegressionExtractionRecord,
    RepeatResultRecord,
    RunRecord,
    ScenarioResultRecord,
    ShrinkResultRecord,
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
    blob_stem = repeat_id

    transcript_blob = write_json_blob(
        run_blob_dir / f"{blob_stem}_transcript.json.gz",
        _to_jsonable(result.turn_results),
    )
    assertions_blob = write_json_blob(
        run_blob_dir / f"{blob_stem}_assertions.json.gz",
        _to_jsonable(result.assertions),
    )
    counterexample_blob = None
    if result.counterexample is not None:
        counterexample_blob = write_json_blob(
            run_blob_dir / f"{blob_stem}_counterexample.json.gz",
            _to_jsonable(result.counterexample),
        )
    raw_error_blob = None
    if result.raw_error:
        raw_error_blob = write_json_blob(
            run_blob_dir / f"{blob_stem}_raw_error.json.gz",
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
                run_blob_dir
                / f"{blob_stem}_assertion_{idx + 1:03d}_counterexample.json.gz",
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


def _save_fuzz_trials_for_repeat(
    *,
    store: LocalResultStore,
    run_id: str,
    scenario_result_id: str,
    result: JobResult,
) -> None:
    if not result.fuzz_trials:
        return
    repeat_id = f"{scenario_result_id}_r{result.repeat_index:03d}"
    run_blob_dir = store.sqlite_path.parent / "blobs" / run_id
    started = result.started_at or _now_iso()
    for trial in result.fuzz_trials:
        tid = trial["trial_index"]
        trial_id = f"{repeat_id}_fuzz{tid:04d}"
        turns = trial.get("turn_results") or ()
        transcript_blob = write_json_blob(
            run_blob_dir / f"{repeat_id}_trial{tid:04d}_transcript.json.gz",
            _to_jsonable(turns),
        )
        details_raw = trial.get("behaviour_details") or ()
        details_list = [dict(d) for d in details_raw] if details_raw else []
        pst = trial.get("per_step_user_turns")
        per_step: tuple[tuple[str, ...], ...] | None = None
        if pst is not None:
            per_step = tuple(tuple(str(u) for u in seg) for seg in pst)
        store.save_fuzz_trial(
            FuzzTrialRecord(
                trial_id=trial_id,
                repeat_result_id=repeat_id,
                trial_index=int(tid),
                seed=trial.get("seed"),
                status=str(trial.get("status", "passed")),  # type: ignore[arg-type]
                user_turns=tuple(str(x) for x in trial.get("user_turns", ())),
                behaviour_labels=tuple(str(x) for x in trial.get("behaviour_labels", ())),
                behaviour_details=tuple(details_list),
                summary_label=str(trial.get("summary_label", "")),
                failure_signature_json=(
                    json.dumps(trial["failure_signature"], sort_keys=True)
                    if trial.get("failure_signature") is not None
                    else None
                ),
                failure_kind=trial.get("failure_kind"),
                failure_message=trial.get("failure_message"),
                started_at=started,
                finished_at=result.finished_at,
                duration_ms=int(float(trial.get("duration_s", 0)) * 1000),
                transcript_blob_path=transcript_blob,
                per_step_user_turns=per_step,
            )
        )


def _save_repeat_auxiliary(
    *,
    store: LocalResultStore,
    run_id: str,
    scenario_result_id: str,
    result: JobResult,
) -> None:
    repeat_id = f"{scenario_result_id}_r{result.repeat_index:03d}"
    for pe in result.phase_errors:
        store.save_phase_error(
            PhaseErrorRecord(
                phase_error_id=f"{repeat_id}_pe_{uuid.uuid4().hex[:10]}",
                repeat_result_id=repeat_id,
                phase=pe["phase"],  # type: ignore[arg-type]
                sub_phase=pe.get("sub_phase"),
                error_kind=str(pe["error_kind"]),
                message=str(pe["message"]),
                traceback_blob_path=pe.get("traceback_blob_path"),
                occurred_at=str(pe["occurred_at"]),
            )
        )
    shrink_rows = list(getattr(result, "shrink_results", ()) or ())
    if not shrink_rows and result.shrink_result:
        shrink_rows = [result.shrink_result]
    for sr in shrink_rows:
        store.save_shrink_result(
            ShrinkResultRecord(
                shrink_id=str(sr["shrink_id"]),
                repeat_result_id=repeat_id,
                source_trial_id=sr.get("source_trial_id"),
                status=str(sr.get("status", "passed")),  # type: ignore[arg-type]
                passes_applied=tuple(str(x) for x in sr.get("passes_applied", ())),
                original_user_turns=tuple(str(x) for x in sr.get("original_user_turns", ())),
                shrunk_user_turns=tuple(str(x) for x in sr.get("shrunk_user_turns", ())),
                candidates_evaluated=int(sr.get("candidates_evaluated", 0)),
                duration_ms=sr.get("duration_ms"),
                started_at=str(sr["started_at"]),
                finished_at=sr.get("finished_at"),
                generative_step_index=sr.get("generative_step_index"),
                step_kind=sr.get("step_kind"),
            )
        )
    rx = result.regression_extraction
    if rx and rx.get("regression_id"):
        store.save_regression(
            RegressionExtractionRecord(
                regression_id=str(rx["regression_id"]),
                run_id=run_id,
                scenario_result_id=scenario_result_id,
                shrink_id=rx.get("shrink_id"),
                source_scenario_key=str(rx.get("source_scenario_key", "")),
                target_file=str(rx["target_file"]),
                function_name=str(rx.get("function_name", "")),
                fingerprint=str(rx.get("fingerprint", "")),
                duplicate_policy=str(rx.get("duplicate_policy", "skip")),
                status=str(rx.get("status", "noop")),  # written | partial | noop | errored | skipped_duplicate
                written_at=rx.get("written_at"),
            )
        )


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
        fuzz_config_json=current.fuzz_config_json,
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


class _InlineExecutor(Executor):
    """Runs ``submit`` synchronously (same code path as process pool, ``n=1``)."""

    def submit(self, fn, /, *args, **kwargs) -> Future:  # type: ignore[override]
        fut: Future = Future()
        try:
            fut.set_result(fn(*args, **kwargs))
        except BaseException as exc:
            fut.set_exception(exc)
        return fut

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:  # type: ignore[override]
        return None


def _make_executor(n: int) -> Executor:
    if n <= 1:
        return _InlineExecutor()
    return ProcessPoolExecutor(max_workers=n)


@dataclass
class GenerativeGroup:
    paths: tuple[str, ...]
    scenario_def: ScenarioDef
    case_index: int
    repeat_index: int
    repeat_total: int
    probe: Any
    enable_shrink: bool
    enable_extract: bool


@dataclass
class NonGenerativeGroup:
    job: ScenarioRepeatJob
    param_labels: dict[str, str]


async def _build_groups_async(
    scenarios: list[ScenarioDef],
    paths: tuple[str, ...],
    *,
    enable_shrink: bool,
    enable_extract: bool,
) -> list[GenerativeGroup | NonGenerativeGroup]:
    from agent_spec_kit.isolated_generative import probe_generative_scenario

    groups: list[GenerativeGroup | NonGenerativeGroup] = []
    for sd in scenarios:
        n_cases = max(1, len(scenario_case_runs(sd)))
        for cix in range(n_cases):
            pr: Any | None = None
            use_gen = False
            if _scenario_body_may_use_generative_orchestrator(sd):
                pr = await probe_generative_scenario(sd, case_index=cix)
                use_gen = bool(pr.applies or (not pr.ok) or (pr.mode is not None))
            for k in range(sd.repeats):
                idx = k + 1
                if use_gen and pr is not None:
                    groups.append(
                        GenerativeGroup(
                            paths=paths,
                            scenario_def=sd,
                            case_index=cix,
                            repeat_index=idx,
                            repeat_total=sd.repeats,
                            probe=pr,
                            enable_shrink=enable_shrink,
                            enable_extract=enable_extract,
                        )
                    )
                else:
                    param_case = scenario_case_runs(sd)[cix]
                    param_labels = {k: (v.name or v.id) for k, v in param_case.items()}
                    groups.append(
                        NonGenerativeGroup(
                            ScenarioRepeatJob(
                                paths=paths,
                                scenario_module=sd.module,
                                scenario_name=sd.name,
                                case_index=cix,
                                repeat_index=idx,
                                repeat_total=sd.repeats,
                                enable_shrink=enable_shrink,
                                enable_extract=enable_extract,
                            ),
                            param_labels=param_labels,
                        )
                    )
    return groups


async def _run_one_group(
    group: GenerativeGroup | NonGenerativeGroup,
    ex: Executor,
    on_progress: Callable[[GenerativeGroup | NonGenerativeGroup, str], None] | None = None,
) -> JobResult:
    from agent_spec_kit.isolated_generative import probe_error_job_result, run_full_generative_repeat
    from agent_spec_kit.runner import run_scenario_job

    if isinstance(group, NonGenerativeGroup):
        if on_progress is not None:
            on_progress(group, "repeat started")
        if isinstance(ex, _InlineExecutor):
            sdef = find_scenario(module=group.job.scenario_module, name=group.job.scenario_name)
            if sdef is None:
                return JobResult(
                    ok=False,
                    scenario_name=group.job.scenario_name,
                    case_id="(not found)",
                    repeat_index=group.job.repeat_index,
                    repeat_total=group.job.repeat_total,
                    detail=(
                        f"scenario not found: {group.job.scenario_module}.{group.job.scenario_name}"
                    ),
                    duration_s=0.0,
                    param_cells={},
                )
            return await run_scenario_job(
                sdef,
                case_index=group.job.case_index,
                repeat_index=group.job.repeat_index,
                repeat_total=group.job.repeat_total,
                enable_shrink=group.job.enable_shrink,
                enable_extract=group.job.enable_extract,
            )
        fut = ex.submit(worker_run_full_repeat_job, group.job)
        return await asyncio.wrap_future(fut)

    sd = group.scenario_def
    probe = group.probe
    if on_progress is not None:
        on_progress(group, f"repeat started ({probe.mode or 'generative'} mode)")
    if not probe.ok:
        msg = probe.phase_errors[0]["message"] if probe.phase_errors else "probe failed"
        kind = probe.phase_errors[0].get("error_kind") if probe.phase_errors else "error"
        return probe_error_job_result(
            sd,
            case_id=probe.case_id,
            param_labels=probe.param_labels,
            repeat_index=group.repeat_index,
            repeat_total=group.repeat_total,
            probe=probe,
            message=msg,
            status="failed" if kind == "FuzzTrialsMismatch" else "error",
            failure_kind=str(kind) if kind else "error",
        )

    return await run_full_generative_repeat(
        sd,
        case_index=group.case_index,
        repeat_index=group.repeat_index,
        repeat_total=group.repeat_total,
        probe=probe,
        enable_shrink=group.enable_shrink,
        enable_extract=group.enable_extract,
        submit_trial=None,
        process_pool=ex,
        pool_paths=group.paths,
        use_process_isolation=not isinstance(ex, _InlineExecutor),
        on_progress=(
            (lambda msg: on_progress(group, msg))
            if on_progress is not None
            else None
        ),
    )


def _scenario_record_key(group: GenerativeGroup | NonGenerativeGroup) -> tuple[str, int]:
    if isinstance(group, NonGenerativeGroup):
        j = group.job
        return (f"{j.scenario_module}.{j.scenario_name}", j.case_index)
    return (f"{group.scenario_def.module}.{group.scenario_def.name}", group.case_index)


def _group_progress_label(group: GenerativeGroup | NonGenerativeGroup) -> str:
    if isinstance(group, NonGenerativeGroup):
        params = ""
        if group.param_labels:
            rendered = ", ".join(f"{k}={v}" for k, v in sorted(group.param_labels.items()))
            params = f" ({rendered})"
        return (
            f"{group.job.scenario_name}{params} "
            f"[{group.job.repeat_index}/{group.job.repeat_total}]"
        )
    labels = getattr(group.probe, "param_labels", {}) or {}
    params = ""
    if labels:
        rendered = ", ".join(f"{k}={v}" for k, v in sorted(labels.items()))
        params = f" ({rendered})"
    return f"{group.scenario_def.name}{params} [{group.repeat_index}/{group.repeat_total}]"


async def _run_scenario_groups(
    scenarios: list[ScenarioDef],
    paths: tuple[str, ...],
    *,
    n_workers: int,
    fail_fast: bool,
    enable_shrink: bool,
    enable_extract: bool,
    on_result: Callable[[GenerativeGroup | NonGenerativeGroup, JobResult], None] | None = None,
    on_progress: Callable[[GenerativeGroup | NonGenerativeGroup, str], None] | None = None,
) -> list[tuple[GenerativeGroup | NonGenerativeGroup, JobResult]]:
    groups = await _build_groups_async(
        scenarios,
        paths,
        enable_shrink=enable_shrink,
        enable_extract=enable_extract,
    )
    ex = _make_executor(n_workers)
    paired: list[tuple[GenerativeGroup | NonGenerativeGroup, JobResult]] = []
    last_progress_at: dict[int, float] = {}
    started_at: dict[int, float] = {}

    def emit_progress(group: GenerativeGroup | NonGenerativeGroup, message: str) -> None:
        gid = id(group)
        now = time.monotonic()
        last_progress_at[gid] = now
        if gid not in started_at:
            started_at[gid] = now
        if on_progress is not None:
            on_progress(group, message)

    try:
        if fail_fast:
            for g in groups:
                emit_progress(g, "queued")
                r = await _run_one_group(g, ex, on_progress=emit_progress)
                paired.append((g, r))
                if on_result is not None:
                    on_result(g, r)
                if not r.ok:
                    break
        else:
            async def _run_and_pair(group: GenerativeGroup | NonGenerativeGroup) -> tuple[GenerativeGroup | NonGenerativeGroup, JobResult]:
                emit_progress(group, "queued")
                return group, await _run_one_group(group, ex, on_progress=emit_progress)

            tasks = [asyncio.create_task(_run_and_pair(g)) for g in groups]
            task_to_group = dict(zip(tasks, groups, strict=True))

            async def monitor_idle_heartbeat() -> None:
                heartbeat_s = 60.0
                while True:
                    await asyncio.sleep(1.0)
                    now = time.monotonic()
                    any_pending = False
                    for t, g in task_to_group.items():
                        if t.done():
                            continue
                        any_pending = True
                        gid = id(g)
                        last = last_progress_at.get(gid, started_at.get(gid, now))
                        if now - last >= heartbeat_s:
                            elapsed = int(now - started_at.get(gid, now))
                            emit_progress(g, f"still running ({elapsed}s elapsed)")
                    if not any_pending:
                        return

            idle_task = asyncio.create_task(monitor_idle_heartbeat())
            for task in asyncio.as_completed(tasks):
                g, r = await task
                paired.append((g, r))
                if on_result is not None:
                    on_result(g, r)
            await idle_task
    finally:
        ex.shutdown(wait=True, cancel_futures=False)

    return paired


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


def _run_clear(*, skip_prompt: bool, input_fn: Any = input) -> int:
    import shutil

    root = StorageConfig().root
    if not root.exists():
        emit_note(f"local result store {root} does not exist; nothing to clear.")
        return 0
    resolved = root.resolve()
    print(f"About to delete the local result store at: {resolved}")
    if not skip_prompt:
        try:
            answer = input_fn("Type 'yes' to confirm: ").strip().lower()
        except EOFError:
            answer = ""
        if answer != "yes":
            emit_note("aborted (no changes made).")
            return 1
    shutil.rmtree(root)
    emit_note(f"deleted {resolved}")
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
    run_p.add_argument(
        "--shrink",
        action="store_true",
        help="activate scenario-declared ShrinkConfig after fuzz failures (per-trial isolation)",
    )
    run_p.add_argument(
        "--extract",
        action="store_true",
        help="activate scenario-declared ExtractionConfig to emit regression source",
    )
    sub.add_parser("runs", help="show recent runs")
    show_p = sub.add_parser("show", help="show one run")
    show_p.add_argument("run_id", help="run id")
    reg_p = sub.add_parser("regressions", help="list regression extractions recorded for a run")
    reg_p.add_argument("run_id", help="run id")
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
    clear_p = sub.add_parser(
        "clear",
        help="delete the local result store (all runs, scenarios, blobs)",
    )
    clear_p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="skip the interactive 'yes' confirmation",
    )
    args = parser.parse_args(argv)
    if args.cmd == "clear":
        return _run_clear(skip_prompt=args.yes)
    store = LocalResultStore(StorageConfig())
    if args.cmd == "runs":
        rows = store.list_runs(limit=20)
        for row in rows:
            print(
                f"{row['run_id']}  {row['experiment_name']:<16}  {row['status']:<7}  "
                f"{row['scenario_passed']}/{row['scenario_count']} scenarios  {row['started_at']}"
            )
        return 0
    if args.cmd == "regressions":
        rows = store.list_regressions_for_run(args.run_id)
        if not rows:
            emit_note(f"no regressions for run {args.run_id!r}")
            return 0
        for row in rows:
            print(
                f"{row.get('regression_id')}  {row.get('status'):<18}  "
                f"{row.get('target_file')}  {row.get('function_name')}"
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
                fuzz_config_json=None,
            )
            scenario_records[(f"{sd.module}.{sd.name}", case_index)] = record
            scenario_repeats[record.scenario_result_id] = []
            store.save_scenario_result(record)

    path_tuple = tuple(str(p) for p in paths)
    if not scenarios:
        print("0 passed, 0 failed (no scenarios)")
        return 0

    eff_n = 1 if args.fail_fast and args.n > 1 else args.n
    if args.fail_fast and args.n > 1:
        emit_note("--fail-fast runs serially (-n ignored)")

    paired = asyncio.run(
        _run_scenario_groups(
            scenarios,
            path_tuple,
            n_workers=eff_n,
            fail_fast=args.fail_fast,
            enable_shrink=args.shrink,
            enable_extract=args.extract,
            on_result=lambda _group, result: emit_job_compact(result),
            on_progress=lambda group, msg: emit_note(f"progress: {_group_progress_label(group)}: {msg}"),
        )
    )
    results: list[JobResult] = []
    for group, r in paired:
        results.append(r)
        job_key = _scenario_record_key(group)
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
        _save_fuzz_trials_for_repeat(
            store=store,
            run_id=run_id,
            scenario_result_id=sr.scenario_result_id,
            result=r,
        )
        _save_repeat_auxiliary(
            store=store,
            run_id=run_id,
            scenario_result_id=sr.scenario_result_id,
            result=r,
        )
        if r.fuzz_config_json and sr.fuzz_config_json is None:
            scenario_records[job_key] = dataclasses.replace(sr, fuzz_config_json=r.fuzz_config_json)
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
            emit_trial_failure_detail(r)
    emit_summary_table(results)
    summary = store.compute_run_summary(run_id)
    store.finish_run(run_id, summary)
    failed = sum(1 for r in results if not r.ok)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
