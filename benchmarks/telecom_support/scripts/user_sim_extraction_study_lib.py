"""User-simulation extraction-only study library."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from statistics import median
from typing import Any

import agent_spec_kit as ek
from agent_spec_kit.extraction_impl import extract_regression
from agent_spec_kit.generative import FailureSignature
from agent_spec_kit.isolated_generative import probe_generative_scenario
from agent_spec_kit.registries import ScenarioDef
from agent_spec_kit.runner import JobResult, run_scenario_job

from study_failure_signatures import classify_rerun_match, signatures_equivalent
from user_sim_shrink_study_lib import (
    BENCH,
    bootstrap_sim_records,
    capture_candidate,
    candidate_id,
    discover_sim_scenarios,
    find_case_index,
    flat_turns,
    load_results,
    refresh_candidate_signatures,
    regression_id,
    save_results,
)

EXTRACTION_DIR = BENCH / "tasks" / "extraction"
EXTRACTED_SIM_DIR = BENCH / "tasks" / "regressions" / "extracted_sim"
CONFIG_PATH = EXTRACTION_DIR / "study_config.yaml"


def load_extraction_study_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    import yaml  # type: ignore[import-untyped]

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def extraction_config(cfg: dict[str, Any]) -> ek.ExtractionConfig:
    ext = cfg.get("extraction", {})
    return ek.ExtractionConfig(
        target_file=ext.get("target_file", "../../regressions/extracted_sim/all_regressions.py"),
        add_tags=("telecom", "regression", "user-sim", "extracted-sim"),
    )


def extraction_target_path(scenario_def: ScenarioDef, cfg: dict[str, Any]) -> Path:
    from agent_spec_kit.extraction_impl import _target_path

    return _target_path(scenario_def, extraction_config(cfg))


def failure_signature_from_job(job: JobResult) -> FailureSignature | None:
    if job.counterexample is not None:
        return FailureSignature.from_counterexample(job.counterexample)
    if job.failure_kind:
        return FailureSignature(check_kind=job.failure_kind, path=None, assertion_id=None)
    return None


def signatures_match(target: FailureSignature | None, observed: FailureSignature | None) -> bool:
    return signatures_equivalent(target, observed)


def count_user_turns(candidate: dict[str, Any]) -> int:
    per = candidate.get("captured_per_step") or {}
    return len(flat_turns({int(k): tuple(v) for k, v in per.items()}))


async def extract_failure(
    scenario_def: ScenarioDef,
    candidate: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Extract regression: concretise sim scenario with captured user-sim transcript turns."""
    task_id = candidate["task_id"]
    seed = int(candidate.get("persona_seed", 0))
    reg_id = regression_id(task_id, seed)
    case_index = int(candidate["case_index"])
    per_step = {
        int(k): tuple(str(x) for x in v)
        for k, v in (candidate.get("captured_per_step") or {}).items()
    }
    flat = flat_turns(per_step)
    target_sig = FailureSignature.from_dict(candidate.get("failure_signature"))
    ext_cfg = extraction_config(cfg)
    probe = await probe_generative_scenario(scenario_def, case_index=case_index)
    ext = extract_regression(
        scenario_def=scenario_def,
        failure_signature=target_sig.as_dict() if target_sig else {},
        extraction=ext_cfg,
        regression_id=reg_id,
        body_steps=tuple(probe.steps),
        concrete_per_generative_step=per_step,
    )
    extraction_format = "ast_concrete"
    if ext.status == "errored" and flat:
        ext = extract_regression(
            scenario_def=scenario_def,
            failure_signature=target_sig.as_dict() if target_sig else {},
            extraction=ext_cfg,
            regression_id=reg_id,
            shrunk_user_turns=flat,
        )
        extraction_format = "legacy_user_messages"
    target_path = extraction_target_path(scenario_def, cfg)
    file_ok = target_path.exists() and ext.status in (
        "written",
        "partial",
        "skipped_duplicate",
    )
    import_ok = False
    collected = False
    if file_ok:
        try:
            ast.parse(target_path.read_text(encoding="utf-8"))
            import_ok = True
        except SyntaxError:
            import_ok = False
    fn_name = ext.function_name
    if import_ok and fn_name:
        text = target_path.read_text(encoding="utf-8")
        collected = f"async def {fn_name}" in text or f"def {fn_name}" in text
    if file_ok:
        invalidate_extracted_scenario_cache()
    return {
        "regression_id": reg_id,
        "source_failure_id": candidate.get("id") or candidate_id(task_id, seed),
        "task_id": task_id,
        "persona_seed": seed,
        "user_turns": count_user_turns(candidate),
        "extraction_format": extraction_format,
        "extraction_status": ext.status,
        "function_name": fn_name,
        "target_path": str(target_path.relative_to(BENCH)),
        "file_generated": file_ok,
        "imports_ok": import_ok,
        "collected": collected,
        "reproduces_failure": False,
        "rerun_ok": None,
        "rerun_status": None,
        "failure_signature_on_rerun": None,
        "message": ext.message,
    }


_EXTRACTED_SCENARIOS: dict[str, ScenarioDef] | None = None
_SIM_SCENARIO_DIR = BENCH / "tasks" / "user_simulation" / "scenarios"


def _import_extracted_sim_modules() -> None:
    """Import regression modules (not named test_*.py; discovery only scans those)."""
    from agent_spec_kit.discovery import import_path

    for path in sorted(EXTRACTED_SIM_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        import_path(path.resolve())


def load_registry_for_extracted_rerun() -> None:
    """Register sim study fixtures plus extracted regression scenarios."""
    global _EXTRACTED_SCENARIOS
    from agent_spec_kit.discovery import collect_module_paths, import_paths
    from agent_spec_kit.registries import iter_scenarios, reset_registries

    reset_registries()
    import_paths(collect_module_paths(_SIM_SCENARIO_DIR))
    sim_names = {sdef.name for sdef in iter_scenarios()}
    _import_extracted_sim_modules()
    _EXTRACTED_SCENARIOS = {
        sdef.name: sdef for sdef in iter_scenarios() if sdef.name not in sim_names
    }


def discover_extracted_scenario(function_name: str) -> ScenarioDef | None:
    if _EXTRACTED_SCENARIOS is None:
        load_registry_for_extracted_rerun()
    return _EXTRACTED_SCENARIOS.get(function_name) if _EXTRACTED_SCENARIOS else None


def invalidate_extracted_scenario_cache() -> None:
    global _EXTRACTED_SCENARIOS
    _EXTRACTED_SCENARIOS = None


async def validate_extraction_rerun(
    extraction_record: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Run extracted scenario and fill rerun + reproduces_failure fields."""
    target_sig = FailureSignature.from_dict(candidate.get("failure_signature"))
    fn = extraction_record.get("function_name")
    out = dict(extraction_record)
    out["reproduces_failure"] = False
    out["rerun_ok"] = None
    out["rerun_status"] = None
    out["failure_signature_on_rerun"] = None

    if not extraction_record.get("file_generated") or not fn:
        return out

    sdef = discover_extracted_scenario(str(fn))
    if sdef is None:
        out["collected"] = False
        out["rerun_ok"] = False
        out["rerun_status"] = "not_collected"
        out["reproduces_failure"] = False
        return out

    out["collected"] = True
    job = await run_scenario_job(sdef, case_index=0, repeat_index=1, repeat_total=1)
    out["rerun_ok"] = job.ok
    out["rerun_status"] = job.status
    observed = failure_signature_from_job(job)
    if observed is not None:
        out["failure_signature_on_rerun"] = observed.as_dict()
    else:
        out["failure_signature_on_rerun"] = {
            "check_kind": job.failure_kind,
            "path": None,
            "assertion_id": None,
        }
    out["rerun_outcome_class"] = classify_rerun_match(
        target=target_sig,
        observed=observed,
        job_ok=bool(job.ok),
    )
    if out["rerun_outcome_class"] == "same_signature":
        out["reproduces_failure"] = True
    return out


def extraction_summary(results: dict[str, Any]) -> dict[str, Any]:
    sim_records = results.get("sim_records") or []
    candidates = results.get("candidates") or []
    eligible = [c for c in candidates if c.get("capture_status") == "ok"]
    extracted = [c for c in candidates if c.get("extraction")]
    ex_rows = [c["extraction"] for c in extracted]
    n_ex = len(ex_rows)
    imp = sum(1 for e in ex_rows if e.get("imports_ok"))
    col = sum(1 for e in ex_rows if e.get("collected"))
    repro = sum(1 for e in ex_rows if e.get("reproduces_failure"))
    dup = sum(1 for e in ex_rows if e.get("extraction_status") == "skipped_duplicate")
    turns = [e.get("user_turns") for e in ex_rows if e.get("user_turns") is not None]
    rerun_same = sum(1 for e in ex_rows if e.get("rerun_outcome_class") == "same_signature")
    rerun_passed = sum(1 for e in ex_rows if e.get("rerun_outcome_class") == "passed")
    rerun_diff_kind = sum(1 for e in ex_rows if e.get("rerun_outcome_class") == "different_check_kind")
    rerun_diff_loc = sum(1 for e in ex_rows if e.get("rerun_outcome_class") == "same_check_different_location")
    return {
        "simulated_conversations": len(sim_records),
        "failing_conversations": len([r for r in sim_records if r.get("failure_signature")]),
        "capture_ok_eligible": len(eligible),
        "capture_failed": len([c for c in candidates if c.get("capture_status") != "ok"]),
        "regressions_extracted": n_ex,
        "import_success_rate_pct": round(100 * imp / n_ex, 1) if n_ex else 0.0,
        "collection_success_rate_pct": round(100 * col / n_ex, 1) if n_ex else 0.0,
        "same_failure_reproduction_rate_pct": round(100 * repro / n_ex, 1) if n_ex else 0.0,
        "rerun_same_signature": rerun_same,
        "rerun_passed": rerun_passed,
        "rerun_different_check_kind": rerun_diff_kind,
        "rerun_same_check_different_location": rerun_diff_loc,
        "median_user_turns": float(median(turns)) if turns else 0.0,
        "duplicate_skips": dup,
    }


def load_candidates_from_shrink_json(path: Path) -> list[dict[str, Any]] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    cands = data.get("candidates")
    return list(cands) if cands else None


__all__ = [
    "BENCH",
    "CONFIG_PATH",
    "EXTRACTION_DIR",
    "EXTRACTED_SIM_DIR",
    "bootstrap_sim_records",
    "capture_candidate",
    "discover_sim_scenarios",
    "extract_failure",
    "extraction_summary",
    "find_case_index",
    "load_candidates_from_shrink_json",
    "load_extraction_study_config",
    "load_results",
    "refresh_candidate_signatures",
    "save_results",
    "validate_extraction_rerun",
]
