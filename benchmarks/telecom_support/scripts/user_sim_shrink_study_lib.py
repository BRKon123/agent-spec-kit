"""User-simulation shrink + regression extraction study library."""

from __future__ import annotations

import ast
import asyncio
import importlib
import json
import re
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

import agent_spec_kit as ek
from agent_spec_kit.extraction_impl import extract_regression
from agent_spec_kit.fixture_graph import scenario_case_runs
from agent_spec_kit.generative import FailureSignature
from agent_spec_kit.isolated_generative import (
    _collect_generative_steps,
    _run_single_trial,
    merged_generative_steps,
    probe_generative_scenario,
    verify_shrink_candidate_async,
)
from agent_spec_kit.registries import ScenarioDef
from agent_spec_kit.runner import run_scenario_job
from agent_spec_kit.scenario_core import _FuzzConversationStep, _SimulateStep
from agent_spec_kit.shrink_engine import shrink_user_turns
from user_simulation_lib import (
    BENCH,
    REPO,
    discover_user_sim_scenarios,
    record_from_job,
    write_transcript,
)

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

CONFIG_PATH = BENCH / "tasks" / "shrinking" / "study_config.yaml"
SHRINK_DIR = BENCH / "tasks" / "shrinking"
REGRESSIONS_DIR = BENCH / "tasks" / "regressions"


def load_shrink_study_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def estimate_tokens(text: str) -> int:
    return len(text.split())


def estimate_turn_tokens(turns: tuple[str, ...]) -> int:
    return sum(estimate_tokens(t) for t in turns)


def _task_from_tags(tags: tuple[str, ...]) -> str | None:
    for t in tags:
        if t.startswith("task:"):
            return t.split(":", 1)[1]
    return None


def _is_sim(tags: tuple[str, ...]) -> bool:
    return "method:sim" in tags


def discover_sim_scenarios(cfg: dict[str, Any]) -> list[tuple[str, ScenarioDef]]:
    tasks = set(cfg["primary_tasks"])
    out: list[tuple[str, ScenarioDef]] = []
    for sdef in discover_user_sim_scenarios():
        task = _task_from_tags(sdef.tags)
        if task in tasks and _is_sim(sdef.tags):
            out.append((task, sdef))
    return sorted(out, key=lambda x: x[0])


def _seed_from_case_id(case_id: str) -> int | None:
    m = re.search(r"seed(\d+)_", case_id)
    return int(m.group(1)) if m else None


def candidate_id(task_id: str, seed: int) -> str:
    return f"SIM-{task_id}-{seed}"


def regression_id(task_id: str, seed: int) -> str:
    return f"REG-SIM-{task_id}-{seed}"


def find_case_index(scenario_def: ScenarioDef, case_id: str) -> int | None:
    from agent_spec_kit.isolated_generative import _case_id_suffix

    for idx, param_case in enumerate(scenario_case_runs(scenario_def)):
        if _case_id_suffix(param_case) == case_id:
            return idx
    return None


def bootstrap_sim_records(cfg: dict[str, Any], study_path: Path) -> tuple[list[dict], str]:
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
        row = dict(rec)
        row["transcript_path"] = str(tpath.relative_to(BENCH))
        row["case_index"] = case_index
        records.append(row)
    return records, study.get("run_id", "bootstrap")


def user_messages_from_transcript(transcript: dict[str, Any]) -> list[str]:
    msgs: list[str] = []
    for turn in transcript.get("turn_results") or []:
        if turn.get("actor") == "user":
            text = turn.get("output") or turn.get("text") or turn.get("content") or ""
            if str(text).strip():
                msgs.append(str(text).strip())
    return msgs


def merged_step_to_generative(
    steps: list[Any],
    captured_per_step: dict[int, tuple[str, ...]],
    merged_step: int,
) -> int:
    """Map step index in merged replay back to original generative step index."""
    gen_ix = [
        i
        for i, st in enumerate(steps)
        if isinstance(st, (_SimulateStep, _FuzzConversationStep))
    ]
    m = 0
    for i, st in enumerate(steps):
        if isinstance(st, (_SimulateStep, _FuzzConversationStep)):
            for _ in captured_per_step.get(i, ()):
                if m == merged_step:
                    return i
                m += 1
        else:
            if m == merged_step:
                for j in reversed(gen_ix):
                    if j <= i:
                        return j
                return gen_ix[-1] if gen_ix else 0
            m += 1
    return gen_ix[-1] if gen_ix else 0


def generative_simulate_steps(steps: list[Any]) -> list[tuple[int, _SimulateStep]]:
    return [
        (i, st)
        for i, st in enumerate(steps)
        if isinstance(st, _SimulateStep)
    ]


def split_user_turns_across_segments(
    user_msgs: list[str],
    gen_steps: list[tuple[int, _SimulateStep]],
) -> dict[int, tuple[str, ...]]:
    if not gen_steps:
        return {}
    if len(gen_steps) == 1:
        return {gen_steps[0][0]: tuple(user_msgs)}
    k = len(gen_steps)
    n = len(user_msgs)
    out: dict[int, tuple[str, ...]] = {}
    idx = 0
    for i, (step_i, st) in enumerate(gen_steps):
        remaining_segs = k - i
        remaining_msgs = n - idx
        if i == k - 1:
            take = remaining_msgs
        else:
            min_needed = remaining_segs - 1
            max_take = min(st.max_turns, max(0, remaining_msgs - min_needed))
            take = max(1, max_take) if remaining_msgs > min_needed else remaining_msgs
        out[step_i] = tuple(user_msgs[idx : idx + take])
        idx += take
    return out


def flat_turns(per_step: dict[int, tuple[str, ...]]) -> tuple[str, ...]:
    flat: list[str] = []
    for step_i in sorted(per_step):
        flat.extend(per_step[step_i])
    return tuple(flat)


def failure_signature_display(sig: FailureSignature | None) -> str | None:
    if sig is None:
        return None
    parts = [p for p in (sig.check_kind, sig.path, sig.assertion_id) if p]
    return ":".join(parts) if parts else None


def build_shrink_config(cfg: dict[str, Any]) -> ek.ShrinkConfig:
    passes: list[Any] = []
    for name in cfg.get("shrink", {}).get("passes", ()):
        if name == "remove_user_turns":
            passes.append(ek.shrink.remove_user_turns())
        elif name == "simplify_user_messages":
            passes.append(ek.shrink.simplify_user_messages())
        elif name == "llm_semantic_simplify":
            model = cfg.get("shrink", {}).get("llm_model", "openai:gpt-5-nano")
            passes.append(
                ek.shrink.llm_semantic_simplify(
                    model=model,
                    candidates_per_message=int(
                        cfg.get("shrink", {}).get("candidates_per_message", 3)
                    ),
                )
            )
    confirm = int(cfg.get("confirm_runs", 2))
    max_attempts = cfg.get("shrink", {}).get("max_attempts_per_shrink")
    return ek.ShrinkConfig(
        passes=tuple(passes),
        confirm_runs=confirm,
        max_attempts_per_shrink=int(max_attempts) if max_attempts is not None else None,
    )


async def replay_with_captured(
    scenario_def: ScenarioDef,
    *,
    case_index: int,
    captured_per_step: dict[int, tuple[str, ...]],
) -> tuple[bool, FailureSignature | None, int | None]:
    probe = await probe_generative_scenario(scenario_def, case_index=case_index)
    if not probe.steps:
        return True, None, None
    merged = merged_generative_steps(probe.steps, captured_per_step, {})
    ok, cx, sig, _turns, _err = await _run_single_trial(
        scenario_def,
        param_case=probe.param_case,
        merged_steps=merged,
    )
    failing_step: int | None = None
    if cx is not None:
        sig = FailureSignature.from_counterexample(cx)
        m = re.search(r"step\s+(\d+)", cx.location or "")
        if m:
            failing_step = merged_step_to_generative(
                probe.steps, captured_per_step, int(m.group(1))
            )
    if failing_step is None:
        gen_ix = [
            i
            for i, st in enumerate(probe.steps)
            if isinstance(st, (_SimulateStep, _FuzzConversationStep))
        ]
        failing_step = gen_ix[-1] if gen_ix else 0
    return ok, sig, failing_step


async def classify_stability(
    scenario_def: ScenarioDef,
    *,
    case_index: int,
    captured_per_step: dict[int, tuple[str, ...]],
    failing_step_index: int,
    target_sig: FailureSignature,
    confirm_runs: int,
) -> Literal["stable", "flaky", "non_reproducing"]:
    probe = await probe_generative_scenario(scenario_def, case_index=case_index)
    turns = captured_per_step.get(failing_step_index, ())
    if not turns:
        return "non_reproducing"
    outcome = await verify_shrink_candidate_async(
        scenario_def,
        param_case=probe.param_case,
        original_steps=probe.steps,
        generative_step_index=failing_step_index,
        candidate_turns=turns,
        captured_per_step=captured_per_step,
        target_sig=target_sig,
        confirm_runs=confirm_runs,
    )
    if outcome.matched:
        return "stable"
    if outcome.failure_signature_json:
        return "flaky"
    return "non_reproducing"


async def capture_candidate(
    scenario_def: ScenarioDef,
    *,
    task_id: str,
    case_index: int,
    transcript_path: Path,
    record: dict[str, Any],
) -> dict[str, Any] | None:
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    user_msgs = user_messages_from_transcript(transcript)
    probe = await probe_generative_scenario(scenario_def, case_index=case_index)
    gen_steps = generative_simulate_steps(probe.steps)
    captured = split_user_turns_across_segments(user_msgs, gen_steps)
    ok, sig, failing_step = await replay_with_captured(
        scenario_def, case_index=case_index, captured_per_step=captured
    )
    seed = record.get("seed")
    if seed is None:
        seed = _seed_from_case_id(record.get("case_id", ""))
    cid = candidate_id(task_id, int(seed or 0))
    base = {
        "id": cid,
        "task_id": task_id,
        "persona_seed": seed,
        "scenario_name": scenario_def.name,
        "case_id": record.get("case_id"),
        "case_index": case_index,
        "transcript_path": str(transcript_path.relative_to(BENCH)),
        "failure_signature_display": record.get("failure_signature"),
        "tool_path_signature": record.get("tool_path_signature"),
        "turn_count": record.get("turn_count"),
        "token_count": estimate_turn_tokens(flat_turns(captured)),
        "original_user_turns": list(flat_turns(captured)),
    }
    if ok or sig is None:
        base["capture_status"] = "failed"
        return base
    if failing_step is None:
        gen_ix = [i for i, st in enumerate(probe.steps) if isinstance(st, (_SimulateStep, _FuzzConversationStep))]
        failing_step = gen_ix[-1] if gen_ix else 0
    base.update(
        {
            "capture_status": "ok",
            "failure_signature": sig.as_dict(),
            "captured_per_step": {str(k): list(v) for k, v in captured.items()},
            "failing_step_index": failing_step,
        }
    )
    return base


async def shrink_one_candidate(
    scenario_def: ScenarioDef,
    candidate: dict[str, Any],
    shrink_cfg: ek.ShrinkConfig,
) -> dict[str, Any]:
    case_index = int(candidate["case_index"])
    probe = await probe_generative_scenario(scenario_def, case_index=case_index)
    captured = {
        int(k): tuple(str(x) for x in v)
        for k, v in candidate.get("captured_per_step", {}).items()
    }
    target_sig = FailureSignature.from_dict(candidate.get("failure_signature"))
    if target_sig is None:
        return {"shrink_status": "skipped", "reason": "no signature"}
    step_i = int(candidate.get("failing_step_index", 0))
    source = captured.get(step_i, ())
    t0 = time.perf_counter()

    async def batch_verify(cands: list[tuple[str, ...]]) -> list[bool]:
        out: list[bool] = []
        for cand in cands:
            o = await verify_shrink_candidate_async(
                scenario_def,
                param_case=probe.param_case,
                original_steps=probe.steps,
                generative_step_index=step_i,
                candidate_turns=cand,
                captured_per_step=captured,
                target_sig=target_sig,
                confirm_runs=shrink_cfg.confirm_runs,
            )
            out.append(o.matched)
        return out

    try:
        shrunk, attempts = await shrink_user_turns(
            original=source,
            shrinking=shrink_cfg,
            verify_batch=batch_verify,
        )
    except BaseException as e:
        return {
            "shrink_status": "error",
            "error": str(e),
            "shrink_time_s": time.perf_counter() - t0,
        }
    shrunk_captured = dict(captured)
    shrunk_captured[step_i] = shrunk
    orig_turns = len(source)
    orig_tokens = estimate_turn_tokens(source)
    shrunk_tokens = estimate_turn_tokens(shrunk)
    turn_red = (1.0 - len(shrunk) / orig_turns) * 100 if orig_turns else 0.0
    token_red = (1.0 - shrunk_tokens / orig_tokens) * 100 if orig_tokens else 0.0
    verify_ok = await batch_verify([shrunk])
    return {
        "shrink_status": "ok" if verify_ok[0] else "failed_verify",
        "same_signature_preserved": verify_ok[0],
        "original_turns": orig_turns,
        "shrunk_turns": len(shrunk),
        "turn_reduction_pct": round(turn_red, 1),
        "original_tokens": orig_tokens,
        "shrunk_tokens": shrunk_tokens,
        "token_reduction_pct": round(token_red, 1),
        "verification_attempts": attempts,
        "shrink_time_s": round(time.perf_counter() - t0, 2),
        "shrunk_per_step": {str(k): list(v) for k, v in shrunk_captured.items()},
        "shrunk_user_turns": list(flat_turns(shrunk_captured)),
    }


def _extraction_config(cfg: dict[str, Any]) -> ek.ExtractionConfig:
    ext = cfg.get("extraction", {})
    return ek.ExtractionConfig(
        target_file=ext.get("target_file", "extracted_sim_regressions.py"),
        add_tags=("telecom", "regression", "user-sim"),
    )


async def extract_one_candidate(
    scenario_def: ScenarioDef,
    candidate: dict[str, Any],
    shrink_result: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    task_id = candidate["task_id"]
    seed = int(candidate.get("persona_seed", 0))
    reg_id = regression_id(task_id, seed)
    case_index = int(candidate["case_index"])
    probe = await probe_generative_scenario(scenario_def, case_index=case_index)
    per_step = {
        int(k): tuple(str(x) for x in v)
        for k, v in shrink_result.get("shrunk_per_step", candidate.get("captured_per_step", {})).items()
    }
    target_sig = FailureSignature.from_dict(candidate.get("failure_signature"))
    extraction = scenario_def.extraction or _extraction_config(cfg)
    ext = extract_regression(
        scenario_def=scenario_def,
        failure_signature=target_sig.as_dict() if target_sig else {},
        extraction=extraction,
        regression_id=reg_id,
        body_steps=tuple(probe.steps),
        concrete_per_generative_step=per_step,
    )
    target_path = REGRESSIONS_DIR / extraction.target_file.split("/")[-1]
    file_ok = target_path.exists() and ext.status in ("written", "partial", "skipped_duplicate")
    import_ok = False
    collected = False
    reproduces = False
    if file_ok:
        try:
            ast.parse(target_path.read_text(encoding="utf-8"))
            import_ok = True
        except SyntaxError:
            import_ok = False
    fn_name = ext.function_name
    if import_ok and fn_name:
        try:
            from agent_spec_kit.discovery import collect_module_paths, import_paths
            from agent_spec_kit.registries import iter_scenarios, reset_registries

            reset_registries()
            import_paths(collect_module_paths(REGRESSIONS_DIR))
            for sdef in iter_scenarios():
                if sdef.name == fn_name:
                    collected = True
                    job = await run_scenario_job(
                        sdef, case_index=0, repeat_index=1, repeat_total=1
                    )
                    if not job.ok:
                        reproduces = True
                    break
        except Exception:
            pass
    return {
        "regression_id": reg_id,
        "source_failure_id": candidate["id"],
        "task_id": task_id,
        "extraction_status": ext.status,
        "function_name": fn_name,
        "file_generated": file_ok,
        "imports_ok": import_ok,
        "collected": collected,
        "reproduces_failure": reproduces,
        "shrunk_turns": shrink_result.get("shrunk_turns"),
        "message": ext.message,
    }


def select_for_shrink_from_extraction(
    results: dict[str, Any],
    extraction_path: Path,
    *,
    limit: int,
) -> int:
    """Mark up to ``limit`` candidates that reproduced failure in the extraction study."""
    ext = json.loads(extraction_path.read_text(encoding="utf-8"))
    repro_ids = {
        c["id"]
        for c in ext.get("candidates") or []
        if (c.get("extraction") or {}).get("reproduces_failure")
    }
    pool = [
        c
        for c in results.get("candidates") or []
        if c.get("id") in repro_ids and c.get("capture_status") == "ok"
    ]
    picked = set(
        c["id"]
        for c in stratified_pick(pool, limit, key_fn=lambda x: x.get("task_id", ""))
    )
    for cand in results.get("candidates") or []:
        cand["selected_for_shrink"] = cand.get("id") in picked
    return len(picked)


def stratified_pick(items: list[dict[str, Any]], limit: int, key_fn) -> list[dict[str, Any]]:
    """Pick up to limit items, spreading across key_fn buckets."""
    if len(items) <= limit:
        return items
    buckets: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        k = key_fn(it)
        buckets.setdefault(k, []).append(it)
    picked: list[dict[str, Any]] = []
    keys = sorted(buckets)
    while len(picked) < limit and any(buckets[k] for k in keys):
        for k in keys:
            if buckets[k] and len(picked) < limit:
                picked.append(buckets[k].pop(0))
    return picked


def save_results(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def load_results(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"phases": {}, "candidates": [], "summary": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def merge_summary(results: dict[str, Any]) -> dict[str, Any]:
    sim_records = results.get("sim_records") or []
    candidates = results.get("candidates") or []
    stable = [c for c in candidates if c.get("stability") == "stable"]
    shrunk = [c for c in candidates if c.get("shrink", {}).get("shrink_status") == "ok"]
    extracted = [c for c in candidates if c.get("extraction", {}).get("file_generated")]
    return {
        "simulated_conversations": len(sim_records),
        "failing_conversations": len([r for r in sim_records if r.get("failure_signature")]),
        "stable_failures": len(stable),
        "flaky_or_non_reproducing": len(candidates)
        - len([c for c in candidates if c.get("stability") == "stable"]),
        "stable_pool_selected": len([c for c in candidates if c.get("selected_for_shrink")]),
        "shrunk_ok": len(shrunk),
        "extracted_ok": len(extracted),
    }


__all__ = [
    "BENCH",
    "CONFIG_PATH",
    "SHRINK_DIR",
    "capture_candidate",
    "classify_stability",
    "discover_sim_scenarios",
    "estimate_turn_tokens",
    "extract_one_candidate",
    "load_results",
    "load_shrink_study_config",
    "merge_summary",
    "record_from_job",
    "save_results",
    "shrink_one_candidate",
    "select_for_shrink_from_extraction",
    "stratified_pick",
    "write_transcript",
]
