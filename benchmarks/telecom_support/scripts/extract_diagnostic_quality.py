#!/usr/bin/env python3
"""Merge panels + framework messages; LLM-score specificity (A--E) per cell."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
load_dotenv(REPO / ".env")
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from diagnostic_comparison.shared.run_framework import (
    collect_all_framework_messages,
    format_agent_spec_kit,
    framework_loc,
    run_framework,
)
from scripts.diagnostic_quality_lib import (
    FAILURES_DIR,
    FRAMEWORKS,
    META_PATH,
    MESSAGES_PATH,
    RECORDS_PATH,
    cell_metrics,
    deterministic_metrics,
    diagnostic_targets,
    load_results_enriched,
    parse_failure_panels,
    require_openai_key,
    score_cells,
    witness_to_dict,
)
from scripts.fault_detection_lib import DEFAULT_FAULT_LOG, ELIGIBILITY_PATH, RESULTS_PATH


def _failure_box(
    family: str,
    task: str,
    oracle: str,
    framework: str,
    witness,
    messages: dict,
) -> str:
    sid = f"{family}|{task}"
    block = messages.get(sid)
    if isinstance(block, dict) and framework in block:
        return str(block[framework])
    if framework == "agent_spec_kit":
        return format_agent_spec_kit(witness)
    return run_framework(framework, witness)


def build_cells(
    results: dict,
    panels: dict,
    messages: dict,
    targets: dict[str, str],
    *,
    main_table: bool,
    ceiling: bool,
) -> list[dict]:
    f_detected: set[tuple[str, str]] = set()
    for rec in results.values():
        if rec.get("detected") and rec.get("oracle") == "F":
            f_detected.add((rec["fault"], rec["task"]))

    cells: list[dict] = []
    seen: set[str] = set()

    if main_table:
        for family, task in sorted(f_detected):
            scenario = f"test_f{family[1:]}_t{task[1:]}_full"
            witness = panels.get(scenario)
            if witness is None:
                continue
            for fw in FRAMEWORKS:
                key = f"{family}|{task}|{fw}|F"
                if key in seen:
                    continue
                seen.add(key)
                rec = results.get(f"{family}|{task}|F", {})
                box = _failure_box(family, task, "F", fw, witness, messages)
                cell = {
                    "key": key,
                    "family": family,
                    "task": task,
                    "framework": fw,
                    "oracle": "F",
                    "detected": True,
                    "diagnostic_target": targets.get(family, ""),
                    "failure_box_text": box,
                    "witness": witness_to_dict(witness),
                    **cell_metrics(box, witness, framework=fw),
                    "custom_diagnostic_loc": (
                        0 if fw == "agent_spec_kit" else framework_loc(fw, family, task)
                    ),
                }
                cell["passed"] = rec.get("passed")
                cells.append(cell)

    if ceiling:
        for family, task in sorted(f_detected):
            for oracle in "O", "S", "T", "F":
                kind = {"O": "output", "S": "state", "T": "trace", "F": "full"}[oracle]
                scenario = f"test_f{family[1:]}_t{task[1:]}_{kind}"
                rec = results.get(f"{family}|{task}|{oracle}", {})
                if rec.get("passed") is not False:
                    continue
                witness = panels.get(scenario)
                if witness is None:
                    continue
                fw = "agent_spec_kit"
                key = f"{family}|{task}|{fw}|{oracle}"
                if key in seen:
                    continue
                seen.add(key)
                box = witness.panel_text or witness.headline
                cells.append(
                    {
                        "key": key,
                        "family": family,
                        "task": task,
                        "framework": fw,
                        "oracle": oracle,
                        "detected": rec.get("detected"),
                        "diagnostic_target": targets.get(family, ""),
                        "failure_box_text": box,
                        "witness": witness_to_dict(witness),
                        **deterministic_metrics(witness),
                        "custom_diagnostic_loc": 0,
                        "passed": rec.get("passed"),
                        "section": "oracle_ceiling",
                    }
                )
    return cells


async def _run(args: argparse.Namespace) -> int:
    if not args.log.is_file():
        print(f"Missing log: {args.log}", file=sys.stderr)
        return 1
    if not args.results.is_file():
        print(f"Missing results: {args.results}", file=sys.stderr)
        return 1

    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    panels = parse_failure_panels(log_text)
    results = load_results_enriched(args.results, args.eligibility)
    messages: dict = {}
    if args.messages.is_file():
        messages = yaml.safe_load(args.messages.read_text(encoding="utf-8")) or {}
    targets = diagnostic_targets()

    existing: dict[str, dict] = {}
    if args.merge_existing and RECORDS_PATH.is_file():
        existing = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))

    cells = build_cells(
        results,
        panels,
        messages,
        targets,
        main_table=not args.ceiling_only,
        ceiling=not args.main_only,
    )

    if args.slots:
        wanted = {s.strip() for s in args.slots.split(",")}
        cells = [c for c in cells if c["key"].split("|")[0] + "|" + c["key"].split("|")[1] in wanted or c["key"] in wanted]

    for cell in cells:
        prev = existing.get(cell["key"], {})
        if prev.get("llm_assessment") and not args.refresh_llm:
            cell["llm_assessment"] = prev["llm_assessment"]
            if prev.get("llm_columns"):
                cell["llm_columns"] = prev["llm_columns"]
                for key in (
                    "failed_requirement_named",
                    "trace_node_identified",
                    "field_path_shown",
                    "expected_vs_actual_shown",
                    "stable_signature",
                ):
                    if key in prev:
                        cell[key] = prev[key]
            cell["status"] = prev.get("status", "ok")

    if not args.skip_llm:
        require_openai_key()
        cells = list(
            await score_cells(
                cells,
                model=args.model,
                concurrency=args.workers,
                skip_llm=False,
                refresh_llm=args.refresh_llm,
            )
        )

    out = {c["key"]: c for c in cells}
    if args.merge_existing:
        out = {**existing, **out}

    RECORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECORDS_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    FAILURES_DIR.mkdir(parents=True, exist_ok=True)
    for cell in cells:
        name = cell["key"].replace("|", "_") + ".txt"
        (FAILURES_DIR / name).write_text(cell.get("failure_box_text", ""), encoding="utf-8")

    meta = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "log_path": str(args.log.relative_to(BENCH)),
        "model": args.model,
        "cell_count": len(cells),
        "scored_ok": sum(1 for c in cells if c.get("status") == "ok"),
        "llm_errors": sum(1 for c in cells if c.get("status") == "llm_error"),
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {RECORDS_PATH} ({len(out)} keys)")
    print(f"Wrote {META_PATH}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=DEFAULT_FAULT_LOG)
    ap.add_argument("--results", type=Path, default=RESULTS_PATH)
    ap.add_argument("--eligibility", type=Path, default=ELIGIBILITY_PATH)
    ap.add_argument("--messages", type=Path, default=MESSAGES_PATH)
    ap.add_argument("--model", default="openai:gpt-5-nano")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument("--refresh-llm", action="store_true")
    ap.add_argument("--merge-existing", action="store_true", default=True)
    ap.add_argument("--ceiling-only", action="store_true")
    ap.add_argument("--main-only", action="store_true")
    ap.add_argument("--slots", type=str, default=None)
    args = ap.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
