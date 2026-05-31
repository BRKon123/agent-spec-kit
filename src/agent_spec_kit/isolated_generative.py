"""Generative scenarios: probe, per-process fuzz trials, shrink verification, extraction."""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from concurrent.futures import Executor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from agent_spec_kit.extraction_impl import extract_regression
from agent_spec_kit.failures import (
    Counterexample,
    FailureRecord,
    ScenarioAssertionFailed,
    counterexample_from_failure,
)
from agent_spec_kit.fixture_graph import TeardownFn, resolve_fixtures, scenario_case_runs
from agent_spec_kit.fuzz.summary import render_trial_summary
from agent_spec_kit.fuzz_context import build_fuzz_segment_context, strategy_eager_generation
from agent_spec_kit.fuzz_types import GeneratedTurn
from agent_spec_kit.generative import CapturedEpisode, FailureSignature
from agent_spec_kit.param_cases import Case
from agent_spec_kit.registries import ScenarioDef
from agent_spec_kit.run import ConversationTurn
from agent_spec_kit.scenario_core import (
    _FuzzConversationStep,
    _SimulateStep,
    _Step,
    _UserMessageStep,
    create_scenario,
    scenario_fuzz_metadata,
)
from agent_spec_kit.shrink_engine import shrink_user_turns


def _collect_generative_steps(
    steps: list[_Step],
) -> tuple[list[tuple[int, _FuzzConversationStep]], list[tuple[int, _SimulateStep]]]:
    fuzz: list[tuple[int, _FuzzConversationStep]] = []
    sim: list[tuple[int, _SimulateStep]] = []
    for i, st in enumerate(steps):
        if isinstance(st, _FuzzConversationStep):
            fuzz.append((i, st))
        elif isinstance(st, _SimulateStep):
            sim.append((i, st))
    return fuzz, sim


def _validate_uniform_trials(fuzz_steps: list[tuple[int, _FuzzConversationStep]]) -> None:
    if len(fuzz_steps) <= 1:
        return
    got = [st.trials for _, st in fuzz_steps]
    if len(set(got)) != 1:
        msg = f"all fuzz_conversation steps must share the same trials count; got {got}"
        raise ValueError(msg)


def _user_turns_slice(turns: list[ConversationTurn], start: int) -> tuple[str, ...]:
    out: list[str] = []
    for j in range(start, len(turns)):
        t = turns[j]
        if t.actor == "user":
            o = t.output
            out.append(o if isinstance(o, str) else str(o) if o is not None else "")
    return tuple(out)


def _fuzz_segment_index(original_steps: list[_Step], step_index: int) -> int:
    return sum(
        1 for j in range(step_index) if isinstance(original_steps[j], _FuzzConversationStep)
    )


def _rng_for_fuzz_step(
    fst: _FuzzConversationStep,
    *,
    trial: int,
    segment_k: int,
) -> random.Random:
    return random.Random((fst.fuzz_config.seed or 0) + trial * 100_003 + segment_k * 7919)


async def _generate_fuzz_turns(
    fst: _FuzzConversationStep,
    *,
    rng: random.Random,
    segment_index: int,
    turn_results: tuple[ConversationTurn, ...],
) -> tuple[GeneratedTurn, ...]:
    strategy = fst.fuzz_config.strategy
    context = None
    if segment_index > 0 or not strategy_eager_generation(strategy):
        context = build_fuzz_segment_context(
            turn_results,
            segment_index=segment_index,
        )
    generated = await strategy.generate(
        rng=rng,
        max_user_turns=fst.max_user_turns,
        seed_inputs=fst.fuzz_config.seed_inputs,
        context=context,
    )
    return tuple(generated)


def _flat_user_turns_from_breakdown(breakdown: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    flat: list[str] = []
    for seg in breakdown:
        flat.extend(seg)
    return tuple(flat)


def merged_generative_steps(
    original_steps: list[_Step],
    captured_per_step: dict[int, tuple[str, ...]],
    overrides: dict[int, tuple[str, ...]],
) -> list[_Step]:
    """Replace fuzz/simulate steps with concrete ``user_message`` steps."""
    out: list[_Step] = []
    for i, st in enumerate(original_steps):
        if isinstance(st, (_FuzzConversationStep, _SimulateStep)):
            turns = overrides.get(i)
            if turns is None:
                turns = captured_per_step.get(i, ())
            out.extend(_UserMessageStep(m) for m in turns)
        else:
            out.append(st)
    return out


def _format_error(exc: BaseException) -> str:
    if isinstance(exc, AssertionError):
        return str(exc) or "AssertionError"
    if isinstance(exc, BaseException):  # noqa: TRY004
        return f"{type(exc).__name__}: {exc}"
    return "error"


async def _invoke_scenario_body(
    scenario_def: ScenarioDef,
    *,
    fixture_values: dict[str, Any],
    param_case: dict[str, Case[Any]],
    s: Any,
) -> None:
    from agent_spec_kit.runner import _build_scenario_fn_kwargs, _invoke_maybe_async

    kwargs = _build_scenario_fn_kwargs(
        scenario_def, fixture_values=fixture_values, param_case=param_case, s=s
    )
    await _invoke_maybe_async(scenario_def.fn, **kwargs)
    if s.has_pending_steps:
        await s.materialise()


async def _run_single_trial(
    scenario_def: ScenarioDef,
    *,
    param_case: dict[str, Case[Any]],
    merged_steps: list[_Step],
) -> tuple[bool, Counterexample | None, FailureSignature | None, tuple[ConversationTurn, ...], str | None]:
    teardowns: list[TeardownFn] = []
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
        s._steps = list(merged_steps)
        s._executed_until = 0
        await s.materialise()
        return True, None, None, tuple(s._turn_results), None
    except ScenarioAssertionFailed as e:
        sig = FailureSignature.from_counterexample(e.counterexample)
        return False, e.counterexample, sig, tuple(s._turn_results), None
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
        cx = counterexample_from_failure(record)
        sig = FailureSignature.from_counterexample(cx)
        return False, cx, sig, tuple(s._turn_results), None
    except BaseException as e:
        detail = _format_error(e)
        return False, None, None, (), detail
    finally:
        for td in reversed(teardowns):
            try:
                await td()
            except Exception:  # noqa: S110
                pass


async def _run_trial_with_breakdown(
    scenario_def: ScenarioDef,
    *,
    param_case: dict[str, Case[Any]],
    original_steps: list[_Step],
    fuzz_messages_by_index: dict[int, tuple[str, ...]],
    trial_index: int = 0,
) -> tuple[
    bool,
    Counterexample | None,
    FailureSignature | None,
    tuple[ConversationTurn, ...],
    str | None,
    tuple[tuple[str, ...], ...],
]:
    teardowns: list[TeardownFn] = []
    s: Any = None
    breakdown_list: list[tuple[str, ...]] = [()] * len(original_steps)
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

        for i, st in enumerate(original_steps):
            s._executed_until = i
            if isinstance(st, _FuzzConversationStep):
                seg_k = _fuzz_segment_index(original_steps, i)
                if i in fuzz_messages_by_index and strategy_eager_generation(st.fuzz_config.strategy):
                    msgs = fuzz_messages_by_index[i]
                else:
                    rng = _rng_for_fuzz_step(st, trial=trial_index, segment_k=seg_k)
                    generated = await _generate_fuzz_turns(
                        st,
                        rng=rng,
                        segment_index=seg_k,
                        turn_results=tuple(s._turn_results),
                    )
                    msgs = tuple(g.message for g in generated)
                for m in msgs:
                    await s._dispatch_user_message_text(m)
                breakdown_list[i] = tuple(msgs)
            else:
                start = len(s._turn_results)
                await s._dispatch_step(st)
                if isinstance(st, _SimulateStep):
                    breakdown_list[i] = _user_turns_slice(s._turn_results, start)
                elif isinstance(st, _UserMessageStep):
                    breakdown_list[i] = (st.message,)
                else:
                    breakdown_list[i] = ()

        return True, None, None, tuple(s._turn_results), None, tuple(breakdown_list)
    except ScenarioAssertionFailed as e:
        sig = FailureSignature.from_counterexample(e.counterexample)
        return False, e.counterexample, sig, tuple(s._turn_results), None, tuple(breakdown_list)
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
        cx = counterexample_from_failure(record)
        sig = FailureSignature.from_counterexample(cx)
        return False, cx, sig, tuple(s._turn_results), None, tuple(breakdown_list)
    except BaseException as e:
        detail = _format_error(e)
        return False, None, None, (), detail, tuple(breakdown_list)
    finally:
        for td in reversed(teardowns):
            try:
                await td()
            except Exception:  # noqa: S110
                pass


@dataclass(slots=True)
class ProbeResult:
    """Outcome of main-process probe for one (scenario, param case)."""

    ok: bool
    #: True when this scenario+case should use the generative trial worker path (fuzz or simulate+shrink/extract).
    applies: bool
    phase_errors: tuple[dict[str, Any], ...]
    steps: list[_Step]
    fuzz_steps: list[tuple[int, _FuzzConversationStep]]
    sim_steps: list[tuple[int, _SimulateStep]]
    mode: Literal["fuzz", "simulate_only"] | None
    trials_total: int
    fuzz_messages_by_trial: list[dict[int, tuple[str, ...]]]
    seeds: list[int | None]
    fuzz_config_json: str | None
    case_id: str
    param_labels: dict[str, str]
    param_case: dict[str, Case[Any]]
    started_at: str


def _case_id_suffix(param_case: dict[str, Case[Any]]) -> str:
    if not param_case:
        return "default"
    return "+".join(f"{k}={v.id}" for k, v in sorted(param_case.items(), key=lambda kv: kv[0]))


def _param_cell_labels(param_case: dict[str, Case[Any]]) -> dict[str, str]:
    return {k: (c.name or c.id) for k, c in param_case.items()}


async def probe_generative_scenario(
    scenario_def: ScenarioDef,
    *,
    case_index: int,
) -> ProbeResult:
    """Record steps, validate, pre-generate fuzz messages. Runs in the main process."""
    runs = scenario_case_runs(scenario_def)
    if case_index < 0 or case_index >= len(runs):
        return ProbeResult(
            ok=False,
            applies=False,
            phase_errors=(
                {
                    "phase": "probe",
                    "sub_phase": "case_index",
                    "error_kind": "InvalidCaseIndex",
                    "message": f"case_index {case_index} out of range (0..{len(runs) - 1})",
                    "traceback_blob_path": None,
                    "occurred_at": datetime.now(tz=UTC).isoformat(),
                },
            ),
            steps=[],
            fuzz_steps=[],
            sim_steps=[],
            mode=None,
            trials_total=0,
            fuzz_messages_by_trial=[],
            seeds=[],
            fuzz_config_json=None,
            case_id="(invalid case_index)",
            param_labels={},
            param_case={},
            started_at=datetime.now(tz=UTC).isoformat(),
        )


    param_case = runs[case_index]
    case_id = _case_id_suffix(param_case)
    param_labels = _param_cell_labels(param_case)
    started_at = datetime.now(tz=UTC).isoformat()
    phase_errors: list[dict[str, Any]] = []

    want_shrink = scenario_def.shrinking is not None
    want_extract = scenario_def.extraction is not None

    fixture_values, teardowns = await resolve_fixtures(scenario_def, param_case=param_case)
    s_probe: Any = None
    steps: list[_Step] = []
    try:
        a_fix = scenario_def.agent_fixture
        u_fix = scenario_def.user_fixture
        agent = fixture_values.get(a_fix) if a_fix else None
        uagent = fixture_values.get(u_fix) if u_fix else None
        if a_fix and u_fix:
            s_probe = create_scenario(
                agent,
                user=uagent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
                recording=True,
            )
        elif a_fix:
            s_probe = create_scenario(
                agent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
                recording=True,
            )
        elif u_fix:
            s_probe = create_scenario(
                user=uagent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
                recording=True,
            )
        else:  # pragma: no cover
            raise RuntimeError("scenario has neither agent nor user fixture")
        await _invoke_scenario_body(
            scenario_def, fixture_values=fixture_values, param_case=param_case, s=s_probe
        )
        steps = list(s_probe._steps)
    except BaseException as e:
        phase_errors.append(
            {
                "phase": "probe",
                "sub_phase": "record",
                "error_kind": type(e).__name__,
                "message": _format_error(e),
                "traceback_blob_path": None,
                "occurred_at": datetime.now(tz=UTC).isoformat(),
            }
        )
        return ProbeResult(
            ok=False,
            applies=False,
            phase_errors=tuple(phase_errors),
            steps=[],
            fuzz_steps=[],
            sim_steps=[],
            mode=None,
            trials_total=0,
            fuzz_messages_by_trial=[],
            seeds=[],
            fuzz_config_json=None,
            case_id=case_id,
            param_labels=param_labels,
            param_case=param_case,
            started_at=started_at,
        )
    finally:
        for td in reversed(teardowns):
            try:
                await td()
            except Exception:  # noqa: S110
                pass

    fuzz_steps, sim_steps = _collect_generative_steps(steps)
    if fuzz_steps:
        mode: Literal["fuzz", "simulate_only"] | None = "fuzz"
    elif sim_steps and (want_shrink or want_extract):
        mode = "simulate_only"
    else:
        return ProbeResult(
            ok=True,
            applies=False,
            phase_errors=(),
            steps=steps,
            fuzz_steps=fuzz_steps,
            sim_steps=sim_steps,
            mode=None,
            trials_total=0,
            fuzz_messages_by_trial=[],
            seeds=[],
            fuzz_config_json=(
                json.dumps(scenario_fuzz_metadata(s_probe), default=str)
                if s_probe is not None and scenario_fuzz_metadata(s_probe) is not None
                else None
            ),
            case_id=case_id,
            param_labels=param_labels,
            param_case=param_case,
            started_at=started_at,
        )

    try:
        _validate_uniform_trials(fuzz_steps)
    except ValueError as e:
        phase_errors.append(
            {
                "phase": "probe",
                "sub_phase": "validate",
                "error_kind": "FuzzTrialsMismatch",
                "message": str(e),
                "traceback_blob_path": None,
                "occurred_at": datetime.now(tz=UTC).isoformat(),
            }
        )
        return ProbeResult(
            ok=False,
            applies=False,
            phase_errors=tuple(phase_errors),
            steps=steps,
            fuzz_steps=fuzz_steps,
            sim_steps=sim_steps,
            mode=mode,
            trials_total=0,
            fuzz_messages_by_trial=[],
            seeds=[],
            fuzz_config_json=(
                json.dumps(scenario_fuzz_metadata(s_probe), default=str)
                if s_probe is not None and scenario_fuzz_metadata(s_probe) is not None
                else None
            ),
            case_id=case_id,
            param_labels=param_labels,
            param_case=param_case,
            started_at=started_at,
        )

    trials_total = fuzz_steps[0][1].trials if fuzz_steps else 1
    fuzz_messages_by_trial: list[dict[int, tuple[str, ...]]] = []
    seeds: list[int | None] = []

    for trial in range(trials_total):
        fuzz_messages: dict[int, tuple[str, ...]] = {}
        seed_for_trial: int | None = None
        for k, (ix, fst) in enumerate(fuzz_steps):
            if seed_for_trial is None:
                seed_for_trial = (fst.fuzz_config.seed or 0) + trial * 100_003
            if not strategy_eager_generation(fst.fuzz_config.strategy):
                continue
            rng = _rng_for_fuzz_step(fst, trial=trial, segment_k=k)
            generated = await _generate_fuzz_turns(
                fst,
                rng=rng,
                segment_index=k,
                turn_results=(),
            )
            fuzz_messages[ix] = tuple(g.message for g in generated)
        fuzz_messages_by_trial.append(fuzz_messages)
        seeds.append(seed_for_trial)

    fuzz_cfg_json: str | None = None
    if s_probe is not None:
        meta = scenario_fuzz_metadata(s_probe)
        if meta is not None:
            fuzz_cfg_json = json.dumps(meta, default=str)

    return ProbeResult(
        ok=True,
        applies=True,
        phase_errors=(),
        steps=steps,
        fuzz_steps=fuzz_steps,
        sim_steps=sim_steps,
        mode=mode,
        trials_total=trials_total,
        fuzz_messages_by_trial=fuzz_messages_by_trial,
        seeds=seeds,
        fuzz_config_json=fuzz_cfg_json,
        case_id=case_id,
        param_labels=param_labels,
        param_case=param_case,
        started_at=started_at,
    )


async def record_generative_steps_in_worker(
    scenario_def: ScenarioDef,
    *,
    param_case: dict[str, Case[Any]],
) -> list[_Step]:
    """Re-record steps inside a worker process (deterministic scenario bodies only)."""
    fixture_values, teardowns = await resolve_fixtures(scenario_def, param_case=param_case)
    s_probe: Any = None
    try:
        a_fix = scenario_def.agent_fixture
        u_fix = scenario_def.user_fixture
        agent = fixture_values.get(a_fix) if a_fix else None
        uagent = fixture_values.get(u_fix) if u_fix else None
        if a_fix and u_fix:
            s_probe = create_scenario(
                agent,
                user=uagent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
                recording=True,
            )
        elif a_fix:
            s_probe = create_scenario(
                agent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
                recording=True,
            )
        elif u_fix:
            s_probe = create_scenario(
                user=uagent,
                case_values=param_case,
                fixture_values=fixture_values,
                scenario_name=scenario_def.name,
                recording=True,
            )
        else:  # pragma: no cover
            raise RuntimeError("scenario has neither agent nor user fixture")
        await _invoke_scenario_body(
            scenario_def, fixture_values=fixture_values, param_case=param_case, s=s_probe
        )
        return list(s_probe._steps)
    finally:
        for td in reversed(teardowns):
            try:
                await td()
            except Exception:  # noqa: S110
                pass


async def run_single_fuzz_trial_async(
    scenario_def: ScenarioDef,
    *,
    param_case: dict[str, Case[Any]],
    trial_index: int,
    fuzz_messages_by_index: dict[int, tuple[str, ...]],
) -> dict[str, Any]:
    """Execute one trial; used from worker processes."""
    steps = await record_generative_steps_in_worker(scenario_def, param_case=param_case)
    fuzz_steps, _ = _collect_generative_steps(steps)
    labels_all: list[str] = []
    details_all: list[dict[str, Any]] = []
    seed_for_trial: int | None = None
    for k, (ix, fst) in enumerate(fuzz_steps):
        if seed_for_trial is None:
            seed_for_trial = (fst.fuzz_config.seed or 0) + trial_index * 100_003
        seg_k = _fuzz_segment_index(steps, ix)
        rng = _rng_for_fuzz_step(fst, trial=trial_index, segment_k=seg_k)
        generated = await _generate_fuzz_turns(
            fst,
            rng=rng,
            segment_index=seg_k,
            turn_results=(),
        )
        labels_all.extend(g.label for g in generated)
        details_all.extend(dict(g.detail) for g in generated)

    if fuzz_steps:
        summary_label = render_trial_summary(
            labels=labels_all,
            details=details_all,
            fuzz_config=fuzz_steps[0][1].fuzz_config,
        )
    else:
        summary_label = "simulate"

    t0 = time.perf_counter()
    ok_t, cx, sig, turns, raw_err, breakdown = await _run_trial_with_breakdown(
        scenario_def,
        param_case=param_case,
        original_steps=steps,
        fuzz_messages_by_index=fuzz_messages_by_index,
        trial_index=trial_index,
    )
    duration_s = time.perf_counter() - t0
    flat_turns = _flat_user_turns_from_breakdown(breakdown)
    trial_status: str = "passed" if ok_t else "failed"
    cx_payload: dict[str, Any] | None = None
    if cx is not None:
        cx_payload = {
            "headline": cx.headline,
            "location": cx.location,
            "path": cx.path,
            "expected_summary": cx.expected_summary,
            "actual_min": cx.actual_min,
            "notes": tuple(cx.notes),
            "check_kind": cx.check_kind,
            "location_detail": cx.location_detail,
        }
    return {
        "trial_index": trial_index,
        "seed": seed_for_trial if seed_for_trial is not None else trial_index,
        "status": trial_status,
        "user_turns": flat_turns,
        "per_step_user_turns": breakdown,
        "behaviour_labels": tuple(labels_all),
        "behaviour_details": tuple(details_all),
        "summary_label": summary_label,
        "failure_message": (cx.headline if cx else raw_err),
        "failure_kind": (cx.check_kind if cx else ("error" if raw_err else None)),
        "duration_s": duration_s,
        "turn_results": turns,
        "failure_signature": sig.as_dict() if sig else None,
        "counterexample": cx_payload,
        "ok": ok_t,
    }


@dataclass(slots=True)
class ShrinkVerifyOutcome:
    matched: bool
    failure_signature_json: str | None
    duration_ms: int


async def verify_shrink_candidate_async(
    scenario_def: ScenarioDef,
    *,
    param_case: dict[str, Case[Any]],
    original_steps: list[_Step],
    generative_step_index: int,
    candidate_turns: tuple[str, ...],
    captured_per_step: dict[int, tuple[str, ...]],
    target_sig: FailureSignature,
    confirm_runs: int,
) -> ShrinkVerifyOutcome:
    t0 = time.perf_counter()
    merged = merged_generative_steps(original_steps, captured_per_step, {generative_step_index: candidate_turns})
    for _ in range(confirm_runs):
        ok_v, _, sig_v, _, _ = await _run_single_trial(
            scenario_def,
            param_case=param_case,
            merged_steps=merged,
        )
        if ok_v or sig_v is None:
            return ShrinkVerifyOutcome(
                matched=False,
                failure_signature_json=None,
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        if sig_v != target_sig:
            return ShrinkVerifyOutcome(
                matched=False,
                failure_signature_json=json.dumps(sig_v.as_dict(), sort_keys=True),
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
    return ShrinkVerifyOutcome(
        matched=True,
        failure_signature_json=json.dumps(target_sig.as_dict(), sort_keys=True),
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )


async def shrink_extract_after_trials(
    scenario_def: ScenarioDef,
    *,
    probe: ProbeResult,
    fuzz_trials: tuple[dict[str, Any], ...],
    enable_shrink: bool,
    enable_extract: bool,
    verify_batch: Any,
    on_progress: Callable[[str], None] | None = None,
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any] | None, tuple[dict[str, Any], ...]]:
    """Shrink (optional) and extract (optional). ``verify_batch(step_i, candidates) -> list[bool]``."""
    want_shrink = bool(enable_shrink and scenario_def.shrinking is not None)
    want_extract = bool(enable_extract and scenario_def.extraction is not None)
    steps = probe.steps
    fuzz_steps, _sim = _collect_generative_steps(steps)
    generative_indices = [i for i, st in enumerate(steps) if isinstance(st, (_FuzzConversationStep, _SimulateStep))]

    episodes: list[CapturedEpisode] = []
    for ft in fuzz_trials:
        sig = FailureSignature.from_dict(ft.get("failure_signature"))
        episodes.append(
            CapturedEpisode(
                segment_kind="fuzz" if fuzz_steps else "simulate",  # type: ignore[arg-type]
                user_turns=tuple(str(x) for x in ft.get("user_turns", ())),
                transcript=tuple(ft.get("turn_results") or ()),
                failure_signature=sig,
                seed=ft.get("seed"),
                trial_index=int(ft["trial_index"]),
            )
        )

    failing = [ep for ep in episodes if ep.failure_signature is not None]
    target_sig: FailureSignature | None = failing[0].failure_signature if failing else None
    failing_trial_index = failing[0].trial_index if failing else None
    captured_per_step: dict[int, tuple[str, ...]] = {}
    if failing and failing_trial_index is not None:
        ft_match = next(
            (x for x in fuzz_trials if int(x["trial_index"]) == int(failing_trial_index)),
            None,
        )
        if ft_match is not None:
            per_step = ft_match.get("per_step_user_turns") or ()
            for i in generative_indices:
                if i < len(per_step):
                    captured_per_step[i] = tuple(str(x) for x in per_step[i])

    phase_errors: list[dict[str, Any]] = []
    shrink_blobs: list[dict[str, Any]] = []
    shrunk_per_step: dict[int, tuple[str, ...]] = {}
    param_case = probe.param_case

    if want_shrink and target_sig is not None and scenario_def.shrinking is not None:
        if on_progress is not None:
            on_progress("shrink phase started")
        shrinking_cfg = scenario_def.shrinking

        async def shrink_one_step(step_i: int) -> tuple[
            int,
            tuple[str, ...] | None,
            dict[str, Any] | None,
            dict[str, Any] | None,
        ]:
            source_turns = captured_per_step.get(step_i, ())
            if not source_turns:
                return step_i, None, None, None
            if on_progress is not None:
                on_progress(f"shrink step {step_i} started")
            shrink_started = datetime.now(tz=UTC).isoformat()
            t_sh0 = time.perf_counter()
            shrink_id = f"shrink_{uuid.uuid4().hex[:12]}"
            step_kind = "fuzz" if isinstance(steps[step_i], _FuzzConversationStep) else "simulate"

            async def batch_verify(cands: Sequence[tuple[str, ...]]) -> list[bool]:
                return await verify_batch(step_i, list(cands))

            try:
                shrunk, candidates = await shrink_user_turns(
                    original=source_turns,
                    shrinking=shrinking_cfg,
                    verify_batch=batch_verify,
                )
                blob = {
                    "shrink_id": shrink_id,
                    "source_trial_id": None,
                    "status": "passed",
                    "passes_applied": tuple(p.kind for p in shrinking_cfg.passes),
                    "original_user_turns": source_turns,
                    "shrunk_user_turns": shrunk,
                    "candidates_evaluated": candidates,
                    "duration_ms": int((time.perf_counter() - t_sh0) * 1000),
                    "started_at": shrink_started,
                    "finished_at": datetime.now(tz=UTC).isoformat(),
                    "generative_step_index": step_i,
                    "step_kind": step_kind,
                }
                if on_progress is not None:
                    on_progress(
                        f"shrink step {step_i} done ({candidates} candidates, {len(shrunk)} turns)"
                    )
                return step_i, shrunk, blob, None
            except BaseException as e:
                pe = {
                    "phase": "shrink",
                    "sub_phase": "engine",
                    "error_kind": type(e).__name__,
                    "message": _format_error(e),
                    "traceback_blob_path": None,
                    "occurred_at": datetime.now(tz=UTC).isoformat(),
                }
                return step_i, source_turns, None, pe

        shrink_tasks = [shrink_one_step(si) for si in generative_indices]
        shrink_parts = await asyncio.gather(*shrink_tasks, return_exceptions=True)
        for part in shrink_parts:
            if isinstance(part, BaseException):
                phase_errors.append(
                    {
                        "phase": "shrink",
                        "sub_phase": "engine",
                        "error_kind": type(part).__name__,
                        "message": _format_error(part),
                        "traceback_blob_path": None,
                        "occurred_at": datetime.now(tz=UTC).isoformat(),
                    }
                )
                continue
            step_i, shrunk, blob, pe = part
            if pe is not None:
                phase_errors.append(pe)
            if shrunk is not None:
                shrunk_per_step[step_i] = shrunk
            if blob is not None:
                shrink_blobs.append(blob)
        shrink_blobs.sort(key=lambda b: int(b.get("generative_step_index", 0)))

    concrete_per_generative_step: dict[int, tuple[str, ...]] = {}
    for gi in generative_indices:
        concrete_per_generative_step[gi] = shrunk_per_step.get(gi, captured_per_step.get(gi, ()))

    regression_blob: dict[str, Any] | None = None
    if want_extract and scenario_def.extraction is not None and target_sig is not None and failing:
        if on_progress is not None:
            on_progress("extract phase started")
        has_turns = any(concrete_per_generative_step.get(gi, ()) for gi in generative_indices)
        if has_turns:
            regression_id = f"reg_{uuid.uuid4().hex[:16]}"
            try:
                ext = extract_regression(
                    scenario_def=scenario_def,
                    failure_signature=target_sig.as_dict(),
                    extraction=scenario_def.extraction,
                    regression_id=regression_id,
                    body_steps=tuple(steps),
                    concrete_per_generative_step=concrete_per_generative_step,
                )
                regression_blob = {
                    "regression_id": regression_id,
                    "shrink_id": shrink_blobs[0]["shrink_id"] if shrink_blobs else None,
                    "source_scenario_key": scenario_def.name,
                    "target_file": scenario_def.extraction.target_file,
                    "function_name": ext.function_name or f"regression_{regression_id}",
                    "fingerprint": ext.fingerprint or regression_id,
                    "duplicate_policy": scenario_def.extraction.duplicate_policy,
                    "status": ext.status,
                    "written_at": (
                        datetime.now(tz=UTC).isoformat()
                        if ext.status in ("written", "partial")
                        else None
                    ),
                    "message": ext.message,
                }
                if ext.status == "errored":
                    phase_errors.append(
                        {
                            "phase": "extract",
                            "sub_phase": "emit",
                            "error_kind": "ExtractionError",
                            "message": ext.message or "extraction failed",
                            "traceback_blob_path": None,
                            "occurred_at": datetime.now(tz=UTC).isoformat(),
                        }
                    )
                if on_progress is not None:
                    on_progress(f"extract phase finished ({ext.status})")
            except BaseException as e:
                phase_errors.append(
                    {
                        "phase": "extract",
                        "sub_phase": "emit",
                        "error_kind": type(e).__name__,
                        "message": _format_error(e),
                        "traceback_blob_path": None,
                        "occurred_at": datetime.now(tz=UTC).isoformat(),
                    }
                )
                if on_progress is not None:
                    on_progress("extract phase errored")

    return tuple(shrink_blobs), regression_blob, tuple(phase_errors)


def failure_context_from_trials(
    probe: ProbeResult,
    trials_sorted: tuple[dict[str, Any], ...],
) -> tuple[FailureSignature | None, dict[int, tuple[str, ...]]]:
    """First failing trial's signature and per-generative-step user turns."""
    steps = probe.steps
    gen_ix = [
        i
        for i, st in enumerate(steps)
        if isinstance(st, (_FuzzConversationStep, _SimulateStep))
    ]
    for ft in trials_sorted:
        sig = FailureSignature.from_dict(ft.get("failure_signature"))
        if sig is None:
            continue
        per_step = ft.get("per_step_user_turns") or ()
        cap: dict[int, tuple[str, ...]] = {}
        for i in gen_ix:
            if i < len(per_step):
                cap[i] = tuple(str(x) for x in per_step[i])
        return sig, cap
    return None, {}


async def run_full_generative_repeat(
    scenario_def: ScenarioDef,
    *,
    case_index: int,
    repeat_index: int,
    repeat_total: int,
    probe: ProbeResult,
    enable_shrink: bool,
    enable_extract: bool,
    submit_trial: Callable[[int, dict[int, tuple[str, ...]]], Awaitable[dict[str, Any]]] | None = None,
    process_pool: Executor | None = None,
    pool_paths: tuple[str, ...] | None = None,
    use_process_isolation: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> Any:
    """One generative repeat: trials via ``submit_trial`` or pool workers, then shrink/extract.

    When ``use_process_isolation`` is True and ``process_pool`` is set, fuzz trials and shrink
    checks run in worker processes. Otherwise everything runs in the current asyncio loop
    (``n=1`` / inline executor).
    """
    from agent_spec_kit.fuzz.driver import pick_fuzzer_driver
    from agent_spec_kit.runner import FuzzTrialJob, ShrinkVerifyJob, worker_run_fuzz_trial, worker_verify_shrink_candidate

    job_started = probe.started_at
    t0 = time.perf_counter()
    driver = pick_fuzzer_driver(probe)
    if on_progress is not None:
        on_progress(f"starting generative repeat ({probe.mode or 'unknown'} mode)")

    async def _submit_trial(ti: int, msgs: dict[int, tuple[str, ...]]) -> dict[str, Any]:
        if submit_trial is not None:
            return await submit_trial(ti, msgs)
        if use_process_isolation and process_pool is not None and pool_paths is not None:
            job = FuzzTrialJob(
                paths=pool_paths,
                scenario_module=scenario_def.module,
                scenario_name=scenario_def.name,
                case_index=case_index,
                repeat_index=repeat_index,
                repeat_total=repeat_total,
                trial_index=ti,
                fuzz_messages_items=tuple(sorted(msgs.items())),
            )
            return await asyncio.wrap_future(process_pool.submit(worker_run_fuzz_trial, job))
        return await run_single_fuzz_trial_async(
            scenario_def,
            param_case=probe.param_case,
            trial_index=ti,
            fuzz_messages_by_index=msgs,
        )

    outcomes = await driver.run(
        submit_trial=_submit_trial,
        trials_total=probe.trials_total,
        fuzz_messages_by_trial=probe.fuzz_messages_by_trial,
        on_trial_started=(
            (lambda ti: on_progress(f"fuzz trial {ti + 1}/{probe.trials_total} started"))
            if on_progress is not None
            else None
        ),
        on_trial_finished=(
            (
                lambda ti, out: on_progress(
                    f"fuzz trial {ti + 1}/{probe.trials_total} finished ({out.get('status', 'unknown')})"
                )
            )
            if on_progress is not None
            else None
        ),
    )
    trials_sorted = tuple(sorted(outcomes, key=lambda d: int(d["trial_index"])))
    any_fail = any(not t.get("ok", True) for t in trials_sorted)
    shrink_rows: tuple[dict[str, Any], ...] = ()
    reg: dict[str, Any] | None = None
    extra_pe: tuple[dict[str, Any], ...] = ()

    target_sig, captured = failure_context_from_trials(probe, trials_sorted)

    async def _await_shrink_future(ix: int, fut: Any) -> tuple[int, bool]:
        outcome = await fut
        return ix, bool(outcome.matched)

    async def submit_shrink_verifies(step_i: int, cands: list[tuple[str, ...]]) -> list[bool]:
        if not cands:
            return []
        if target_sig is None or scenario_def.shrinking is None:
            return [False] * len(cands)
        conf = scenario_def.shrinking.confirm_runs
        captured_items = tuple(sorted(captured.items()))
        total_candidates = len(cands)
        chunk_size = max(1, min(10, total_candidates))
        batches = [cands[i : i + chunk_size] for i in range(0, total_candidates, chunk_size)]
        total_batches = len(batches)
        done = 0
        out_acc: list[bool] = []
        if use_process_isolation and process_pool is not None and pool_paths is not None:
            for bix, batch in enumerate(batches, start=1):
                if on_progress is not None:
                    on_progress(f"shrink step {step_i}: verifying batch {bix}/{total_batches}")
                futs: list[Any] = []
                for j, cand in enumerate(batch):
                    job = ShrinkVerifyJob(
                        paths=pool_paths,
                        scenario_module=scenario_def.module,
                        scenario_name=scenario_def.name,
                        case_index=case_index,
                        generative_step_index=step_i,
                        candidate_turns=cand,
                        captured_items=captured_items,
                        target_sig_dict=target_sig.as_dict(),
                        confirm_runs=conf,
                    )
                    fut = asyncio.wrap_future(process_pool.submit(worker_verify_shrink_candidate, job))
                    futs.append(asyncio.create_task(_await_shrink_future(j, fut)))
                matched_by_index: dict[int, bool] = {}
                for done_task in asyncio.as_completed(futs):
                    ix, matched = await done_task
                    matched_by_index[ix] = matched
                    done += 1
                    if on_progress is not None:
                        on_progress(f"shrink step {step_i}: {done}/{total_candidates} candidates done")
                out_acc.extend(matched_by_index[i] for i in range(len(batch)))
            return out_acc
        steps_r = await record_generative_steps_in_worker(scenario_def, param_case=probe.param_case)
        for bix, batch in enumerate(batches, start=1):
            if on_progress is not None:
                on_progress(f"shrink step {step_i}: verifying batch {bix}/{total_batches}")
            for cand in batch:
                o = await verify_shrink_candidate_async(
                    scenario_def,
                    param_case=probe.param_case,
                    original_steps=steps_r,
                    generative_step_index=step_i,
                    candidate_turns=cand,
                    captured_per_step=dict(captured),
                    target_sig=target_sig,
                    confirm_runs=conf,
                )
                out_acc.append(o.matched)
                done += 1
                if on_progress is not None:
                    on_progress(f"shrink step {step_i}: {done}/{total_candidates} candidates done")
        return out_acc

    if (enable_shrink or enable_extract) and any_fail:
        shrink_rows, reg, extra_pe = await shrink_extract_after_trials(
            scenario_def,
            probe=probe,
            fuzz_trials=trials_sorted,
            enable_shrink=enable_shrink,
            enable_extract=enable_extract,
            verify_batch=submit_shrink_verifies,
            on_progress=on_progress,
        )
    if on_progress is not None:
        on_progress("generative repeat finished")

    return build_generative_job_result(
        scenario_def,
        case_id=probe.case_id,
        param_labels=probe.param_labels,
        repeat_index=repeat_index,
        repeat_total=repeat_total,
        probe=probe,
        fuzz_trials=trials_sorted,
        shrink_results=shrink_rows,
        regression_extraction=reg,
        extra_phase_errors=extra_pe,
        job_started_at=job_started,
        job_t0=t0,
    )


def build_generative_job_result(
    scenario_def: ScenarioDef,
    *,
    case_id: str,
    param_labels: dict[str, str],
    repeat_index: int,
    repeat_total: int,
    probe: ProbeResult,
    fuzz_trials: tuple[dict[str, Any], ...],
    shrink_results: tuple[dict[str, Any], ...],
    regression_extraction: dict[str, Any] | None,
    extra_phase_errors: tuple[dict[str, Any], ...],
    job_started_at: str,
    job_t0: float,
) -> Any:
    """Assemble :class:`~agent_spec_kit.runner.JobResult` for one generative repeat."""
    from agent_spec_kit.runner import JobResult

    steps = probe.steps
    fuzz_steps, _ = _collect_generative_steps(steps)
    overall_ok = all(t.get("ok", t.get("status") == "passed") for t in fuzz_trials)
    detail: str | None = None
    failure_kind: str | None = None
    last_turns: tuple[ConversationTurn, ...] = ()
    for ft in reversed(fuzz_trials):
        tr = ft.get("turn_results") or ()
        if tr:
            last_turns = tuple(tr)
            break

    if not overall_ok:
        for ft in fuzz_trials:
            if ft.get("status") == "failed":
                detail = str(ft.get("failure_message"))
                failure_kind = str(ft.get("failure_kind")) if ft.get("failure_kind") else failure_kind
                break

    duration_s = time.perf_counter() - job_t0
    finished_at = datetime.now(tz=UTC).isoformat()
    shrink_result_first = shrink_results[0] if shrink_results else None
    all_phase = tuple(probe.phase_errors) + tuple(extra_phase_errors)

    return JobResult(
        ok=overall_ok,
        scenario_name=scenario_def.name,
        case_id=case_id,
        repeat_index=repeat_index,
        repeat_total=repeat_total,
        detail=detail,
        duration_s=duration_s,
        counterexample=None,
        param_cells=param_labels,
        status="passed" if overall_ok else "failed",
        started_at=job_started_at,
        finished_at=finished_at,
        output_preview=(
            str(last_turns[-1].output)[:500]
            if last_turns and last_turns[-1].output is not None
            else None
        ),
        failure_kind=failure_kind,
        failure_message=detail if not overall_ok else None,
        turn_results=last_turns,
        assertions=(),
        fuzz_config_json=probe.fuzz_config_json,
        fuzz_trials=tuple({k: v for k, v in ft.items() if k != "ok"} for ft in fuzz_trials),
        shrink_result=shrink_result_first,
        shrink_results=shrink_results,
        regression_extraction=regression_extraction,
        phase_errors=all_phase,
    )


def probe_error_job_result(
    scenario_def: ScenarioDef,
    *,
    case_id: str,
    param_labels: dict[str, str],
    repeat_index: int,
    repeat_total: int,
    probe: ProbeResult,
    message: str,
    status: str,
    failure_kind: str | None,
) -> Any:
    from agent_spec_kit.runner import JobResult

    return JobResult(
        ok=False,
        scenario_name=scenario_def.name,
        case_id=case_id,
        repeat_index=repeat_index,
        repeat_total=repeat_total,
        detail=message,
        duration_s=0.0,
        param_cells=param_labels,
        status=status,  # type: ignore[arg-type]
        started_at=probe.started_at,
        finished_at=datetime.now(tz=UTC).isoformat(),
        failure_kind=failure_kind,
        failure_message=message,
        phase_errors=probe.phase_errors,
        fuzz_config_json=probe.fuzz_config_json,
    )


__all__ = [
    "ProbeResult",
    "ShrinkVerifyOutcome",
    "build_generative_job_result",
    "failure_context_from_trials",
    "merged_generative_steps",
    "probe_error_job_result",
    "probe_generative_scenario",
    "record_generative_steps_in_worker",
    "run_full_generative_repeat",
    "run_single_fuzz_trial_async",
    "shrink_extract_after_trials",
    "verify_shrink_candidate_async",
]
