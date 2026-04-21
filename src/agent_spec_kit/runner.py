"""Execute one scenario job: fixtures, body, auto-materialise, teardown."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from agent_spec_kit.discovery import import_paths
from agent_spec_kit.failures import (
    Counterexample,
    FailureRecord,
    ScenarioAssertionFailed,
    counterexample_from_failure,
)
from agent_spec_kit.fixture_graph import TeardownFn, resolve_fixtures
from agent_spec_kit.registries import ScenarioDef, find_scenario, reset_registries
from agent_spec_kit.scenario_core import _invoke_maybe_async, create_scenario


@dataclass(slots=True)
class JobResult:
    ok: bool
    scenario_name: str
    repeat_index: int
    repeat_total: int
    detail: str | None
    duration_s: float
    counterexample: Counterexample | None = None


def _format_error(exc: BaseException) -> str:
    if isinstance(exc, AssertionError):
        msg = str(exc)
        return msg or "AssertionError"
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    return f"{type(exc).__name__}: {exc}"


async def run_scenario_job(
    scenario_def: ScenarioDef,
    *,
    repeat_index: int,
    repeat_total: int,
) -> JobResult:
    """Resolve fixtures, run the scenario callable, auto-materialise if needed, teardown."""
    t0 = time.perf_counter()
    teardowns: list[TeardownFn] = []
    ok = False
    detail: str | None = None
    counterexample: Counterexample | None = None
    s = None
    try:
        fixture_values, teardowns = await resolve_fixtures(scenario_def)
        agent = fixture_values[scenario_def.agent_fixture]
        s = create_scenario(
            agent,
            fixture_values=fixture_values,
            scenario_name=scenario_def.name,
        )
        kwargs: dict[str, object] = {"s": s}
        for name in scenario_def.fixture_param_names:
            kwargs[name] = fixture_values[name]

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
    except AssertionError as e:
        turn_idx = len(s._turn_results) - 1 if s is not None and s._turn_results else None
        step_ix = s._executed_until if s is not None else 0
        record = FailureRecord(
            scenario_name=scenario_def.name,
            step_index=step_ix,
            step_kind="scenario_body",
            turn_index=turn_idx,
            actual=None,
            matcher_spec=None,
            matcher_errors=(),
            error=e,
        )
        counterexample = counterexample_from_failure(record)
        detail = counterexample.headline
    except BaseException as e:
        detail = _format_error(e)
    finally:
        for td in reversed(teardowns):
            try:
                await td()
            except Exception:
                pass

    duration_s = time.perf_counter() - t0
    return JobResult(
        ok=ok,
        scenario_name=scenario_def.name,
        repeat_index=repeat_index,
        repeat_total=repeat_total,
        detail=detail,
        duration_s=duration_s,
        counterexample=counterexample,
    )


@dataclass(slots=True)
class WorkerJob:
    paths: tuple[str, ...]
    scenario_module: str
    scenario_name: str
    repeat_index: int
    repeat_total: int


def worker_run_job(job: WorkerJob) -> JobResult:
    """Process-pool entry: fresh registries, import paths, run one job."""
    reset_registries()
    paths = [Path(p) for p in job.paths]
    import_paths(paths)
    sdef = find_scenario(module=job.scenario_module, name=job.scenario_name)
    if sdef is None:
        return JobResult(
            ok=False,
            scenario_name=job.scenario_name,
            repeat_index=job.repeat_index,
            repeat_total=job.repeat_total,
            detail=f"scenario not found: {job.scenario_module}.{job.scenario_name}",
            duration_s=0.0,
        )
    return asyncio.run(
        run_scenario_job(
            sdef,
            repeat_index=job.repeat_index,
            repeat_total=job.repeat_total,
        )
    )


__all__ = ["JobResult", "WorkerJob", "run_scenario_job", "worker_run_job"]
