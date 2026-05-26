#!/usr/bin/env python3
"""Collect per-framework failure box text from parsed fault-detection log panels."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from diagnostic_comparison.shared.run_framework import collect_all_framework_messages
from scripts.diagnostic_quality_lib import (
    DIAG_DIR,
    MESSAGES_PATH,
    diagnostic_targets,
    load_results_enriched,
    parse_failure_panels,
)
from scripts.fault_detection_lib import DEFAULT_FAULT_LOG, ELIGIBILITY_PATH, RESULTS_PATH


def _slot_id(family: str, task: str) -> str:
    return f"{family}|{task}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=DEFAULT_FAULT_LOG)
    ap.add_argument("--results", type=Path, default=RESULTS_PATH)
    ap.add_argument("--eligibility", type=Path, default=ELIGIBILITY_PATH)
    ap.add_argument("--out", type=Path, default=MESSAGES_PATH)
    ap.add_argument(
        "--scope",
        choices=("detected_f", "failed_full", "all_failed"),
        default="detected_f",
    )
    args = ap.parse_args()

    if not args.log.is_file():
        print(f"Missing log: {args.log}", file=sys.stderr)
        return 1
    if not args.results.is_file():
        print(f"Missing results: {args.results}", file=sys.stderr)
        return 1

    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    panels = parse_failure_panels(log_text)
    results = load_results_enriched(args.results, args.eligibility)
    targets = diagnostic_targets()

    samples: dict[str, object] = {
        "_meta": {
            "log": str(args.log.relative_to(BENCH)),
            "scope": args.scope,
            "panel_count": len(panels),
        }
    }

    f_detected_tasks: set[tuple[str, str]] = set()
    for key, rec in results.items():
        if rec.get("detected") and rec.get("oracle") == "F":
            f_detected_tasks.add((rec["fault"], rec["task"]))

    count = 0
    for key, rec in sorted(results.items()):
        family, task, oracle = rec["fault"], rec["task"], rec["oracle"]
        if rec.get("passed") is not False:
            continue
        if args.scope == "detected_f":
            if (family, task) not in f_detected_tasks or oracle != "F":
                continue
        elif args.scope == "failed_full":
            if oracle != "F":
                continue
        scenario = rec.get("scenario") or f"test_f{family[1:]}_t{task[1:]}_{'full' if oracle=='F' else {'O':'output','S':'state','T':'trace'}[oracle]}"
        witness = panels.get(scenario)
        if witness is None:
            continue
        sid = _slot_id(family, task)
        block: dict[str, str] = {
            "diagnostic_target": targets.get(family, ""),
            "scenario": scenario,
            "oracle": oracle,
        }
        msgs = collect_all_framework_messages(witness)
        block.update(msgs)
        samples[sid] = block
        count += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        yaml.safe_dump(samples, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    print(f"Wrote {args.out} ({count} slots)")

    md_path = DIAG_DIR / "FAILURE_MESSAGES.md"
    lines = [
        "# Failure messages (diagnostic comparison)",
        "",
        f"Generated from `{args.log.name}`. Scope: `{args.scope}`.",
        "",
    ]
    for sid, block in samples.items():
        if sid == "_meta":
            continue
        lines.append(f"## {sid}")
        if isinstance(block, dict):
            for fw in (
                "agent_spec_kit",
                "pytest_plain",
                "langsmith",
                "pydantic_evals",
                "promptfoo",
                "braintrust",
            ):
                val = block.get(fw, "")
                if val:
                    lines.append(f"- **{fw}**: `{str(val)[:200]}`")
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
