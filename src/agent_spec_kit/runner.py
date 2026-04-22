"""Execute one scenario job: fixtures, body, auto-materialise, teardown."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
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
from agent_spec_kit.scenario_core import _invoke_maybe_async, create_scenario
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
    #: Keys are @parametrize axis names; values are ``name`` or ``id`` (see :func:`_param_cell_labels`).
    param_cells: dict[str, str] = field(default_factory=dict)
    # Back-compat: some call sites use scenario_name for display; case_id is the param slice
    @property
    def display_name(self) -> str:
        if self.case_id == "default":
            return self.scenario_name
        return f"{self.scenario_name} [{self.case_id}]"


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
) -> JobResult:
    """Resolve fixtures, run the scenario, auto-materialise if needed, teardown."""
    t0 = time.perf_counter()
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
        )
    param_case = runs[case_index]
    case_id = _case_id_suffix(param_case)
    param_labels = _param_cell_labels(param_case)
    teardowns: list[TeardownFn] = []
    ok = False
    detail: str | None = None
    counterexample: Counterexample | None = None
    s: Any = None
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
    except BaseException as e:
        detail = _format_error(e)
    finally:
        for td in reversed(teardowns):
            try:
                await td()
            except Exception:  # noqa: S110
                pass

    duration_s = time.perf_counter() - t0
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
    )


@dataclass(slots=True)
class WorkerJob:
    paths: tuple[str, ...]
    scenario_module: str
    scenario_name: str
    case_index: int
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
        )
    )


__all__ = ["JobResult", "WorkerJob", "run_scenario_job", "worker_run_job"]
