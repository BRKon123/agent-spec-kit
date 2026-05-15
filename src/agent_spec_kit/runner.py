"""Execute one scenario job: fixtures, body, auto-materialise, teardown."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_spec_kit.discovery import import_paths
from agent_spec_kit.failures import (
    Counterexample,
    FailureRecord,
    ScenarioAssertionFailed,
    counterexample_from_failure,
)
from agent_spec_kit.fixture_graph import TeardownFn, resolve_fixtures, scenario_case_runs
from agent_spec_kit.registries import ScenarioDef, find_scenario, reset_registries
from agent_spec_kit.scenario_core import (
    _invoke_maybe_async,
    create_scenario,
    scenario_fuzz_metadata,
)
from agent_spec_kit.param_cases import Case


def _case_id_suffix(param_case: dict[str, Case[Any]]) -> str:
    if not param_case:
        return "default"
    return "+".join(f"{k}={v.id}" for k, v in sorted(param_case.items(), key=lambda kv: kv[0]))


def _param_cell_labels(param_case: dict[str, Case[Any]]) -> dict[str, str]:
    """Human-readable label per @parametrize axis: ``Case.name`` if set, else ``id``."""
    return {k: (c.name or c.id) for k, c in param_case.items()}


@dataclass(slots=True)
class JobResult:
    ok: bool
    scenario_name: str
    case_id: str = "default"
    repeat_index: int = 1
    repeat_total: int = 1
    detail: str | None = None
    duration_s: float = 0.0
    counterexample: Counterexample | None = None
    status: str = "passed"
    started_at: str | None = None
    finished_at: str | None = None
    output_preview: str | None = None
    failure_kind: str | None = None
    failure_message: str | None = None
    turn_results: tuple[Any, ...] = ()
    assertions: tuple[dict[str, Any], ...] = ()
    raw_error: str | None = None
    #: Keys are @parametrize axis names; values are ``name`` or ``id`` (see :func:`_param_cell_labels`).
    param_cells: dict[str, str] = field(default_factory=dict)
    #: JSON string for ``scenario_results.fuzz_config_json`` when the scenario fuzzed.
    fuzz_config_json: str | None = None
    #: Trial summaries from ``fuzz_conversation`` (passed to the result store).
    fuzz_trials: tuple[dict[str, Any], ...] = ()
    shrink_result: dict[str, Any] | None = None
    shrink_results: tuple[dict[str, Any], ...] = ()
    regression_extraction: dict[str, Any] | None = None
    phase_errors: tuple[dict[str, Any], ...] = ()
    # Back-compat: some call sites use scenario_name for display; case_id is the param slice
    @property
    def display_name(self) -> str:
        if self.case_id == "default":
            return self.scenario_name
        return f"{self.scenario_name} [{self.case_id}]"


def _scenario_body_may_use_generative_orchestrator(scenario_def: ScenarioDef) -> bool:
    """Avoid probing (and double fixture resolve) for scenarios that cannot need the orchestrator."""
    try:
        src = inspect.getsource(scenario_def.fn)
    except (OSError, TypeError):
        return True
    if "fuzz_conversation(" in src:
        return True
    if "simulate_conversation(" in src and (
        scenario_def.shrinking is not None or scenario_def.extraction is not None
    ):
        return True
    return False


def _format_error(exc: BaseException) -> str:
    if isinstance(exc, AssertionError):
        msg = str(exc)
        return msg or "AssertionError"
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    return f"{type(exc).__name__}: {exc}"


def _inject_scenario_parameter(
    name: str,
    *,
    fixture_values: dict[str, Any],
    param_case: dict[str, Case[Any]],
) -> Any:
    """Resolve one scenario parameter: fixtures, or ``axis`` (value) / ``axis_case`` (full :class:`Case`)."""
    in_fix = name in fixture_values
    in_pc = name in param_case
    if in_fix and in_pc:
        m = (
            f"scenario parameter {name!r} is both a resolved fixture and a @parametrize axis; "
            f"rename one of them"
        )
        raise ValueError(m)
    if in_fix:
        return fixture_values[name]
    if name.endswith("_case"):
        stem = name[: -len("_case")]
        if not stem:
            m = f"invalid scenario parameter {name!r} (use e.g. task_case for @parametrize axis 'task')"
            raise TypeError(m) from None
        if stem in param_case:
            return param_case[stem]
        m = f"no @parametrize axis {stem!r} for {name!r} (this run: {sorted(param_case.keys())!r})"
        raise KeyError(m) from None
    if in_pc:
        return param_case[name].value
    m = (
        f"unknown scenario parameter {name!r}: not a fixture in this run "
        f"({sorted(fixture_values.keys())!r}) and not a param axis "
        f"({sorted(param_case.keys())!r})"
    )
    raise KeyError(m)


def _build_scenario_fn_kwargs(
    scenario_def: ScenarioDef,
    *,
    fixture_values: dict[str, Any],
    param_case: dict[str, Case[Any]],
    s: object,
) -> dict[str, object]:
    out: dict[str, object] = {"s": s}
    for name in scenario_def.fixture_param_names:
        out[name] = _inject_scenario_parameter(name, fixture_values=fixture_values, param_case=param_case)
    return out


async def run_scenario_job(
    scenario_def: ScenarioDef,
    *,
    case_index: int = 0,
    repeat_index: int,
    repeat_total: int,
    enable_shrink: bool = False,
    enable_extract: bool = False,
) -> JobResult:
    """Resolve fixtures, run the scenario, auto-materialise if needed, teardown."""
    t0 = time.perf_counter()
    started_at = datetime.now(tz=UTC).isoformat()
    runs = scenario_case_runs(scenario_def)
    if case_index < 0 or case_index >= len(runs):
        return JobResult(
            ok=False,
            scenario_name=scenario_def.name,
            case_id="(invalid case_index)",
            repeat_index=repeat_index,
            repeat_total=repeat_total,
            detail=f"case_index {case_index} out of range (0..{len(runs) - 1})",
            duration_s=0.0,
            param_cells={},
            status="error",
            started_at=started_at,
            finished_at=datetime.now(tz=UTC).isoformat(),
            failure_kind="invalid_case_index",
            failure_message=f"case_index {case_index} out of range (0..{len(runs) - 1})",
        )
    param_case = runs[case_index]
    case_id = _case_id_suffix(param_case)
    param_labels = _param_cell_labels(param_case)

    if _scenario_body_may_use_generative_orchestrator(scenario_def):
        from agent_spec_kit.isolated_generative import (
            probe_error_job_result,
            probe_generative_scenario,
            run_full_generative_repeat,
            run_single_fuzz_trial_async,
        )

        probe = await probe_generative_scenario(scenario_def, case_index=case_index)
        generative_takeover = probe.applies or (not probe.ok) or (probe.mode is not None)
        if generative_takeover:
            if not probe.ok:
                msg = probe.phase_errors[0]["message"] if probe.phase_errors else "probe failed"
                kind = probe.phase_errors[0].get("error_kind") if probe.phase_errors else "error"
                return probe_error_job_result(
                    scenario_def,
                    case_id=probe.case_id,
                    param_labels=probe.param_labels,
                    repeat_index=repeat_index,
                    repeat_total=repeat_total,
                    probe=probe,
                    message=msg,
                    status="failed" if kind == "FuzzTrialsMismatch" else "error",
                    failure_kind=str(kind) if kind else "error",
                )
            return await run_full_generative_repeat(
                scenario_def,
                case_index=case_index,
                repeat_index=repeat_index,
                repeat_total=repeat_total,
                probe=probe,
                enable_shrink=enable_shrink,
                enable_extract=enable_extract,
                submit_trial=lambda ti, msgs: run_single_fuzz_trial_async(
                    scenario_def,
                    param_case=param_case,
                    trial_index=ti,
                    fuzz_messages_by_index=msgs,
                ),
                process_pool=None,
                pool_paths=None,
            )

    teardowns: list[TeardownFn] = []
    ok = False
    detail: str | None = None
    counterexample: Counterexample | None = None
    s: Any = None
    status = "passed"
    failure_kind: str | None = None
    raw_error: str | None = None
    assertions: list[dict[str, Any]] = []
    try:
        fixture_values, teardowns = await resolve_fixtures(scenario_def, param_case=param_case)
        a_fix = scenario_def.agent_fixture
        u_fix = scenario_def.user_fixture
        agent = fixture_values.get(a_fix) if a_fix else None
        uagent = fixture_values.get(u_fix) if u_fix else None
        if a_fix and u_fix:
            s = create_scenario(
                agent,
                user=uagent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
            )
        elif a_fix:
            s = create_scenario(
                agent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
            )
        elif u_fix:
            s = create_scenario(
                user=uagent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
            )
        else:  # pragma: no cover
            raise RuntimeError("scenario has neither agent nor user fixture")
        kwargs = _build_scenario_fn_kwargs(
            scenario_def, fixture_values=fixture_values, param_case=param_case, s=s
        )

        async def body() -> None:
            await _invoke_maybe_async(scenario_def.fn, **kwargs)
            if s.has_pending_steps:
                await s.materialise()

        if scenario_def.timeout_s is not None:
            await asyncio.wait_for(body(), timeout=scenario_def.timeout_s)
        else:
            await body()
        ok = True
    except ScenarioAssertionFailed as e:
        counterexample = e.counterexample
        detail = counterexample.headline
        status = "failed"
        failure_kind = counterexample.check_kind or "assertion_failure"
        assertions.append(
            {
                "assertion_type": failure_kind,
                "actor": None,
                "turn_index": None,
                "status": "failed",
                "message": detail,
                "details": {
                    "location": counterexample.location,
                    "path": counterexample.path,
                    "expected_summary": counterexample.expected_summary,
                    "actual_min": counterexample.actual_min,
                },
                "counterexample": {
                    "headline": counterexample.headline,
                    "location": counterexample.location,
                    "path": counterexample.path,
                    "expected_summary": counterexample.expected_summary,
                    "actual_min": counterexample.actual_min,
                    "notes": list(counterexample.notes),
                    "check_kind": counterexample.check_kind,
                    "location_detail": counterexample.location_detail,
                    "events": counterexample.events,
                },
            }
        )
    except AssertionError as e:
        turn_idx = len(s._turn_results) - 1 if s is not None and s._turn_results else None
        step_ix = s._executed_until if s is not None else 0
        ev: tuple[Any, ...] | None = None
        if s is not None and s._turn_results and s._turn_results[-1].events:
            ev = tuple(s._turn_results[-1].events)
        tr: tuple[Any, ...] | None
        if s is not None and s._turn_results:
            tr = tuple(s._turn_results)
        else:
            tr = None
        record = FailureRecord(
            scenario_name=scenario_def.name,
            step_index=step_ix,
            step_kind="scenario_body",
            turn_index=turn_idx,
            actual=None,
            matcher_spec=None,
            matcher_errors=(),
            error=e,
            events=ev,
            turn_results=tr,
        )
        counterexample = counterexample_from_failure(record)
        detail = counterexample.headline
        status = "failed"
        failure_kind = counterexample.check_kind or "assertion_failure"
        assertions.append(
            {
                "assertion_type": failure_kind,
                "actor": None,
                "turn_index": turn_idx,
                "status": "failed",
                "message": detail,
                "details": {
                    "location": counterexample.location,
                    "path": counterexample.path,
                    "expected_summary": counterexample.expected_summary,
                    "actual_min": counterexample.actual_min,
                },
                "counterexample": {
                    "headline": counterexample.headline,
                    "location": counterexample.location,
                    "path": counterexample.path,
                    "expected_summary": counterexample.expected_summary,
                    "actual_min": counterexample.actual_min,
                    "notes": list(counterexample.notes),
                    "check_kind": counterexample.check_kind,
                    "location_detail": counterexample.location_detail,
                    "events": counterexample.events,
                },
            }
        )
    except BaseException as e:
        detail = _format_error(e)
        raw_error = detail
        status = "timeout" if isinstance(e, asyncio.TimeoutError) else "error"
        failure_kind = status
    finally:
        for td in reversed(teardowns):
            try:
                await td()
            except Exception:  # noqa: S110
                pass

    duration_s = time.perf_counter() - t0
    fuzz_cfg_json: str | None = None
    fuzz_trials_out: tuple[dict[str, Any], ...] = ()
    if s is not None:
        meta = scenario_fuzz_metadata(s)
        if meta is not None:
            fuzz_cfg_json = json.dumps(meta, default=str)
    return JobResult(
        ok=ok,
        scenario_name=scenario_def.name,
        case_id=case_id,
        repeat_index=repeat_index,
        repeat_total=repeat_total,
        detail=detail,
        duration_s=duration_s,
        counterexample=counterexample,
        param_cells=param_labels,
        status=status if not ok else "passed",
        started_at=started_at,
        finished_at=datetime.now(tz=UTC).isoformat(),
        output_preview=(str(s._turn_results[-1].output)[:500] if s is not None and s._turn_results else None),
        failure_kind=failure_kind,
        failure_message=detail if not ok else None,
        turn_results=tuple(s._turn_results) if s is not None else (),
        assertions=tuple(assertions),
        raw_error=raw_error,
        fuzz_config_json=fuzz_cfg_json,
        fuzz_trials=fuzz_trials_out,
        shrink_result=None,
        shrink_results=(),
        regression_extraction=None,
        phase_errors=(),
    )


@dataclass(slots=True)
class ScenarioRepeatJob:
    """One non-generative scenario repeat (full body in the worker)."""

    paths: tuple[str, ...]
    scenario_module: str
    scenario_name: str
    case_index: int
    repeat_index: int
    repeat_total: int
    enable_shrink: bool = False
    enable_extract: bool = False


WorkerJob = ScenarioRepeatJob


@dataclass(slots=True)
class FuzzTrialJob:
    paths: tuple[str, ...]
    scenario_module: str
    scenario_name: str
    case_index: int
    repeat_index: int
    repeat_total: int
    trial_index: int
    fuzz_messages_items: tuple[tuple[int, tuple[str, ...]], ...]


@dataclass(slots=True)
class ShrinkVerifyJob:
    paths: tuple[str, ...]
    scenario_module: str
    scenario_name: str
    case_index: int
    generative_step_index: int
    candidate_turns: tuple[str, ...]
    captured_items: tuple[tuple[int, tuple[str, ...]], ...]
    target_sig_dict: dict[str, Any]
    confirm_runs: int


def worker_run_full_repeat_job(job: ScenarioRepeatJob) -> JobResult:
    """Process-pool entry: fresh registries, import paths, run one full repeat."""
    reset_registries()
    paths = [Path(p) for p in job.paths]
    import_paths(paths)
    sdef = find_scenario(module=job.scenario_module, name=job.scenario_name)
    if sdef is None:
        return JobResult(
            ok=False,
            scenario_name=job.scenario_name,
            case_id="(not found)",
            repeat_index=job.repeat_index,
            repeat_total=job.repeat_total,
            detail=f"scenario not found: {job.scenario_module}.{job.scenario_name}",
            duration_s=0.0,
            param_cells={},
        )
    return asyncio.run(
        run_scenario_job(
            sdef,
            case_index=job.case_index,
            repeat_index=job.repeat_index,
            repeat_total=job.repeat_total,
            enable_shrink=job.enable_shrink,
            enable_extract=job.enable_extract,
        )
    )


def worker_run_job(job: ScenarioRepeatJob) -> JobResult:
    """Back-compat alias for :func:`worker_run_full_repeat_job`."""
    return worker_run_full_repeat_job(job)


def worker_run_fuzz_trial(job: FuzzTrialJob) -> dict[str, Any]:
    """Run a single generative fuzz/simulate trial in an isolated process."""
    from agent_spec_kit.fixture_graph import scenario_case_runs
    from agent_spec_kit.isolated_generative import run_single_fuzz_trial_async

    reset_registries()
    paths = [Path(p) for p in job.paths]
    import_paths(paths)
    sdef = find_scenario(module=job.scenario_module, name=job.scenario_name)
    if sdef is None:
        return {
            "trial_index": job.trial_index,
            "seed": job.trial_index,
            "status": "error",
            "ok": False,
            "failure_message": f"scenario not found: {job.scenario_module}.{job.scenario_name}",
            "failure_kind": "error",
            "user_turns": (),
            "per_step_user_turns": (),
            "behaviour_labels": (),
            "behaviour_details": (),
            "summary_label": "",
            "duration_s": 0.0,
            "turn_results": (),
            "failure_signature": None,
        }
    runs = scenario_case_runs(sdef)
    param_case = runs[job.case_index]
    fuzz_map = dict(job.fuzz_messages_items)
    return asyncio.run(
        run_single_fuzz_trial_async(
            sdef,
            param_case=param_case,
            trial_index=job.trial_index,
            fuzz_messages_by_index=fuzz_map,
        )
    )


def worker_verify_shrink_candidate(job: ShrinkVerifyJob) -> Any:
    from agent_spec_kit.fixture_graph import scenario_case_runs
    from agent_spec_kit.generative import FailureSignature
    from agent_spec_kit.isolated_generative import ShrinkVerifyOutcome, verify_shrink_candidate_async

    reset_registries()
    paths = [Path(p) for p in job.paths]
    import_paths(paths)
    sdef = find_scenario(module=job.scenario_module, name=job.scenario_name)
    if sdef is None:
        return ShrinkVerifyOutcome(matched=False, failure_signature_json=None, duration_ms=0)
    runs = scenario_case_runs(sdef)
    param_case = runs[job.case_index]
    captured = dict(job.captured_items)
    target = FailureSignature.from_dict(job.target_sig_dict)
    if target is None:
        return ShrinkVerifyOutcome(matched=False, failure_signature_json=None, duration_ms=0)

    async def inner() -> ShrinkVerifyOutcome:
        from agent_spec_kit.isolated_generative import record_generative_steps_in_worker

        steps = await record_generative_steps_in_worker(sdef, param_case=param_case)
        return await verify_shrink_candidate_async(
            sdef,
            param_case=param_case,
            original_steps=steps,
            generative_step_index=job.generative_step_index,
            candidate_turns=job.candidate_turns,
            captured_per_step=captured,
            target_sig=target,
            confirm_runs=job.confirm_runs,
        )

    return asyncio.run(inner())


__all__ = [
    "FuzzTrialJob",
    "JobResult",
    "ScenarioRepeatJob",
    "ShrinkVerifyJob",
    "WorkerJob",
    "_scenario_body_may_use_generative_orchestrator",
    "run_scenario_job",
    "worker_run_full_repeat_job",
    "worker_run_fuzz_trial",
    "worker_run_job",
    "worker_verify_shrink_candidate",
]
