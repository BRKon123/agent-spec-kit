#!/usr/bin/env python3
"""Generate extraction-only markdown report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from user_sim_extraction_study_lib import BENCH, extraction_summary, load_extraction_study_config

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))


def _yes_no(val: bool | None) -> str:
    if val is True:
        return "Yes"
    if val is False:
        return "No"
    return "—"


def main() -> None:
    cfg = load_extraction_study_config()
    path = BENCH / cfg["outputs"]["results_json"]
    if not path.exists():
        raise SystemExit(f"missing results: {path}")
    results = json.loads(path.read_text(encoding="utf-8"))
    summary = extraction_summary(results)
    out = BENCH / cfg["outputs"]["report_md"]

    lines = [
        "# User-simulation regression extraction results",
        "",
        "Shrinking deferred — regressions use **full sim transcript** user turns.",
        "",
        f"Generated: {results.get('generated_utc', '')}",
        "",
        "## Per-failure extraction",
        "",
        "| Regression id | Source failure | Task | Persona | User turns | File | Imports | Collected | Reproduces failure | Rerun status | Extraction status |",
        "|---------------|----------------|------|---------|------------:|------|---------|-----------|-------------------|--------------|-------------------|",
    ]

    snippet_fn = None
    for c in results.get("candidates") or []:
        ex = c.get("extraction")
        if not ex:
            continue
        lines.append(
            f"| {ex.get('regression_id', '—')} | {ex.get('source_failure_id', '—')} | "
            f"{c.get('task_id', '—')} | seed{c.get('persona_seed', '—')} | "
            f"{ex.get('user_turns', '—')} | {_yes_no(ex.get('file_generated'))} | "
            f"{_yes_no(ex.get('imports_ok'))} | {_yes_no(ex.get('collected'))} | "
            f"{_yes_no(ex.get('reproduces_failure'))} | {ex.get('rerun_status') or '—'} | "
            f"{ex.get('extraction_status', '—')} |"
        )
        if snippet_fn is None and ex.get("file_generated") and ex.get("function_name"):
            snippet_fn = ex.get("function_name")

    lines.extend(
        [
            "",
            "## Aggregates",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Simulated conversations | {summary.get('simulated_conversations', 0)} |",
            f"| Failing conversations | {summary.get('failing_conversations', 0)} |",
            f"| Capture ok (eligible) | {summary.get('capture_ok_eligible', 0)} |",
            f"| Capture failed | {summary.get('capture_failed', 0)} |",
            f"| Regressions extracted | {summary.get('regressions_extracted', 0)} |",
            f"| Import success rate | {summary.get('import_success_rate_pct', 0)}% |",
            f"| Collection success rate | {summary.get('collection_success_rate_pct', 0)}% |",
            f"| Same-failure reproduction rate | {summary.get('same_failure_reproduction_rate_pct', 0)}% |",
            f"| Median user turns in extracted test | {summary.get('median_user_turns', 0)} |",
            f"| Duplicate skips | {summary.get('duplicate_skips', 0)} |",
            "",
            "## Example regression snippet",
            "",
        ]
    )

    reg_file = BENCH / "tasks" / "regressions" / "extracted_sim" / "all_regressions.py"
    if snippet_fn and reg_file.exists():
        text = reg_file.read_text(encoding="utf-8")
        needle = f"async def {snippet_fn}"
        start = text.find(needle)
        if start < 0:
            start = text.find("@ek.scenario")
        snippet = text[start : start + 2000] if start >= 0 else text[-2000:]
        lines.append("```python")
        lines.append(snippet.strip())
        lines.append("```")
    else:
        lines.append("_No extracted regression snippet available._")

    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
