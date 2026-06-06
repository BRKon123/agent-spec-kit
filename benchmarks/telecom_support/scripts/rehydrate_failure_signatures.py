#!/usr/bin/env python3
"""Populate structural failure equivalence fields on study JSON records."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.generative import FailureSignature
from agent_spec_kit.isolated_generative import (
    _run_single_trial,
    merged_generative_steps,
    probe_generative_scenario,
)
from agent_spec_kit.runner import run_scenario_job
from agent_spec_kit.scenario_core import _FuzzConversationStep, _SimulateStep
from fuzzing_study_lib import discover_fuzz_study_scenarios
from study_failure_signatures import (
    equivalence_key_from_record,
    failure_fields_from_signature,
    failure_record_fields,
    failure_signature_from_display,
)
from user_sim_shrink_study_lib import generative_simulate_steps, split_user_turns_across_segments


def _task_from_tags(tags: tuple[str, ...]) -> str | None:
    for t in tags:
        if t.startswith("task:"):
            return t.split(":", 1)[1]
    return None


def _scenario_map() -> dict[tuple[str, str], Any]:
    out: dict[tuple[str, str], Any] = {}
    for sdef in discover_fuzz_study_scenarios():
        task = _task_from_tags(sdef.tags)
        if not task:
            continue
        for method in ("manual", "sim", "fuzz"):
            if f"method:{method}" in sdef.tags:
                out[(task, method)] = sdef
    return out


def _case_index(sdef, case_id: str) -> int:
    from agent_spec_kit.isolated_generative import _case_id_suffix

    for idx, param_case in enumerate(scenario_case_runs(sdef)):
        if _case_id_suffix(param_case) == case_id:
            return idx
    return 0


def _generative_step_indices(steps: list[Any]) -> list[int]:
    return [
        i
        for i, st in enumerate(steps)
        if isinstance(st, (_FuzzConversationStep, _SimulateStep))
    ]


def _captured_per_step(rec: dict[str, Any], steps: list[Any]) -> dict[int, tuple[str, ...]]:
    method = rec["method"]
    gen_ix = _generative_step_indices(steps)
    if method == "fuzz":
        per_step = rec.get("per_step_user_turns") or []
        captured: dict[int, tuple[str, ...]] = {}
        for gi, step_i in enumerate(gen_ix):
            if gi < len(per_step) and per_step[gi]:
                captured[step_i] = tuple(str(x) for x in per_step[gi])
        return captured
    if method == "sim":
        msgs = [str(x) for x in (rec.get("mutated_user_messages") or [])]
        if not msgs:
            return {}
        sim_steps = generative_simulate_steps(steps)
        return split_user_turns_across_segments(msgs, sim_steps)
    return {}


async def _replay_frozen(
    rec: dict[str, Any],
    sdef,
) -> FailureSignature | None:
    case_id = rec.get("case_id", "default")
    probe = await probe_generative_scenario(sdef, case_index=_case_index(sdef, str(case_id)))
    captured = _captured_per_step(rec, probe.steps)
    if not captured and rec["method"] != "manual":
        return None
    merged = merged_generative_steps(probe.steps, captured, {})
    ok, cx, sig, _, _ = await _run_single_trial(
        sdef,
        param_case=probe.param_case,
        merged_steps=merged,
    )
    if ok:
        return None
    if cx is not None:
        return FailureSignature.from_counterexample(cx)
    return sig


async def _rehydrate_record(rec: dict[str, Any], scenarios: dict[tuple[str, str], Any]) -> dict[str, Any]:
    if not rec.get("failure_signature"):
        return rec
    task = rec["task_id"]
    method = rec["method"]
    sdef = scenarios.get((task, method))
    if sdef is None:
        return rec

    display = rec["failure_signature"]
    sig: FailureSignature | None = None

    if method == "manual":
        job = await run_scenario_job(
            sdef,
            case_index=_case_index(sdef, str(rec.get("case_id", "default"))),
            repeat_index=1,
            repeat_total=1,
        )
        fields = failure_record_fields(job)
        if fields["failure_signature_struct"] is not None:
            updated = dict(rec)
            updated["failure_signature_struct"] = fields["failure_signature_struct"]
            updated["failure_equivalence_key"] = fields["failure_equivalence_key"]
            return updated

    try:
        sig = await _replay_frozen(rec, sdef)
    except Exception:
        sig = None

    if sig is None and isinstance(display, str):
        sig = failure_signature_from_display(
            display,
            agent_turn_count=rec.get("agent_turn_count"),
        )

    if sig is None:
        return rec

    fields = failure_fields_from_signature(sig, display=display)
    updated = dict(rec)
    updated["failure_signature_struct"] = fields["failure_signature_struct"]
    updated["failure_equivalence_key"] = fields["failure_equivalence_key"]
    return updated


async def _run(args: argparse.Namespace) -> int:
    path = Path(args.study_json)
    if not path.is_absolute():
        path = BENCH / path
    study = json.loads(path.read_text(encoding="utf-8"))
    scenarios = _scenario_map()
    records = study.get("records") or []
    failing = [r for r in records if r.get("failure_signature")]
    sem = asyncio.Semaphore(max(1, args.workers))

    async def _one(rec: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await _rehydrate_record(rec, scenarios)

    print(f"rehydrating {len(failing)} failing records with -n {args.workers}")
    refreshed = await asyncio.gather(*[_one(r) for r in failing])
    refresh_map = {id(old): new for old, new in zip(failing, refreshed, strict=True)}
    updated = [refresh_map.get(id(r), r) for r in records]
    study["records"] = updated
    study["failure_equivalence_rehydrated_utc"] = datetime.now(UTC).isoformat()

    if "summary" in study:
        for method in ("manual", "sim", "fuzz"):
            subset = [r for r in updated if r.get("method") == method]
            if method in study["summary"]:
                study["summary"][method]["distinct_failure_signatures"] = len(
                    {k for r in subset if (k := equivalence_key_from_record(r)) is not None}
                )

    path.write_text(json.dumps(study, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--study-json",
        default="tasks/fuzzing/fuzzing_runs.json",
        help="Study JSON to update in place",
    )
    ap.add_argument("-n", "--workers", type=int, default=8)
    args = ap.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
