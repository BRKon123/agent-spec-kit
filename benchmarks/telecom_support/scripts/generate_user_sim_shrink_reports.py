#!/usr/bin/env python3
"""Generate markdown reports from user_sim_shrink_results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median

from user_sim_shrink_study_lib import BENCH, load_shrink_study_config, merge_summary

if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))


def _pct(vals: list[float]) -> str:
    if not vals:
        return "—"
    return f"{median(vals):.1f}%"


def _med(vals: list[float]) -> str:
    if not vals:
        return "—"
    return f"{median(vals):.2f}"


def write_shrink_report(cfg: dict, results: dict) -> None:
    out = BENCH / cfg["outputs"]["shrink_md"]
    summary = merge_summary(results)
    stab = results.get("stability_counts") or {}
    lines = [
        "# User-simulation shrink study results",
        "",
        f"Generated: {results.get('generated_utc', '')}",
        "",
        "## Candidate / stability",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Simulated conversations | {summary.get('simulated_conversations', 0)} |",
        f"| Failing conversations | {summary.get('failing_conversations', 0)} |",
        f"| Stable failures | {stab.get('stable', summary.get('stable_failures', 0))} |",
        f"| Flaky | {stab.get('flaky', 0)} |",
        f"| Non-reproducing | {stab.get('non_reproducing', 0)} |",
        f"| Capture failed | {stab.get('capture_failed', 0)} |",
        f"| Selected for shrink (cap {cfg['caps']['max_to_shrink']}) | {summary.get('stable_pool_selected', 0)} |",
        f"| Max verification attempts per shrink | {cfg.get('shrink', {}).get('max_attempts_per_shrink', '—')} |",
        "",
        "## Shrink per failure",
        "",
        "| Failure | Task | Persona | Orig turns | Shrunk turns | Turn reduction | Orig tokens | Shrunk tokens | Verif attempts | Same sig | Time (s) |",
        "|---------|------|---------|------------:|-------------:|---------------:|------------:|--------------:|----------------:|---------:|---------:|",
    ]
    for c in results.get("candidates") or []:
        if not c.get("selected_for_shrink"):
            continue
        sh = c.get("shrink") or {}
        if sh.get("shrink_status") != "ok":
            continue
        lines.append(
            f"| {c['id']} | {c['task_id']} | seed{c.get('persona_seed')} | "
            f"{sh.get('original_turns', '—')} | {sh.get('shrunk_turns', '—')} | "
            f"{sh.get('turn_reduction_pct', '—')}% | {sh.get('original_tokens', '—')} | "
            f"{sh.get('shrunk_tokens', '—')} | "
            f"{sh.get('verification_attempts', '—')} | "
            f"{'Yes' if sh.get('same_signature_preserved') else 'No'} | "
            f"{sh.get('shrink_time_s', '—')} |"
        )
    lines.extend(
        [
            "",
            "## All shrink attempts (selected pool)",
            "",
            "| Failure | Task | Persona | Status | Orig turns | Shrunk turns | Verif attempts | Same sig |",
            "|---------|------|---------|--------|------------:|-------------:|----------------:|---------:|",
        ]
    )
    for c in results.get("candidates") or []:
        if not c.get("selected_for_shrink"):
            continue
        sh = c.get("shrink") or {}
        lines.append(
            f"| {c['id']} | {c['task_id']} | seed{c.get('persona_seed')} | "
            f"{sh.get('shrink_status', '—')} | {sh.get('original_turns', '—')} | "
            f"{sh.get('shrunk_turns', '—')} | {sh.get('verification_attempts', '—')} | "
            f"{'Yes' if sh.get('same_signature_preserved') else 'No' if sh else '—'} |"
        )
    shrunk_ok = [c for c in results.get("candidates", []) if c.get("shrink", {}).get("shrink_status") == "ok"]
    turn_red = [c["shrink"]["turn_reduction_pct"] for c in shrunk_ok if "turn_reduction_pct" in c.get("shrink", {})]
    token_red = [c["shrink"]["token_reduction_pct"] for c in shrunk_ok if "token_reduction_pct" in c.get("shrink", {})]
    times = [c["shrink"]["shrink_time_s"] for c in shrunk_ok if "shrink_time_s" in c.get("shrink", {})]
    attempts = [c["shrink"]["verification_attempts"] for c in shrunk_ok if "verification_attempts" in c.get("shrink", {})]
    preserved = sum(1 for c in shrunk_ok if c.get("shrink", {}).get("same_signature_preserved"))
    attempted = sum(1 for c in results.get("candidates", []) if c.get("selected_for_shrink"))
    lines.extend(
        [
            "",
            "## Shrink aggregates",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Stable failures attempted | {attempted} |",
            f"| Successfully shrunk | {len(shrunk_ok)} |",
            f"| Failed to shrink | {attempted - len(shrunk_ok)} |",
            f"| Median turn reduction | {_pct(turn_red)} |",
            f"| Median token reduction | {_pct(token_red)} |",
            f"| Median shrink time (s) | {_med(times)} |",
            f"| Median verification attempts | {_med([float(x) for x in attempts])} |",
            f"| Same-signature preservation rate | {100 * preserved / len(shrunk_ok) if shrunk_ok else 0:.1f}% |",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def write_extraction_report(cfg: dict, results: dict) -> None:
    out = BENCH / cfg["outputs"]["extraction_md"]
    lines = [
        "# User-simulation regression extraction results",
        "",
        "## Extraction table",
        "",
        "| Regression id | Source | Task | Shrunk turns | File | Imports | Collected | Reproduces |",
        "|---------------|--------|------|-------------:|------|---------|-----------|------------|",
    ]
    extracted = []
    for c in results.get("candidates") or []:
        ex = c.get("extraction")
        if not ex:
            continue
        extracted.append((c, ex))
        lines.append(
            f"| {ex.get('regression_id', '—')} | {ex.get('source_failure_id', '—')} | "
            f"{c['task_id']} | {ex.get('shrunk_turns', '—')} | "
            f"{'Yes' if ex.get('file_generated') else 'No'} | "
            f"{'Yes' if ex.get('imports_ok') else 'No'} | "
            f"{'Yes' if ex.get('collected') else 'No'} | "
            f"{'Yes' if ex.get('reproduces_failure') else 'No'} |"
        )
    n = len(extracted)
    imp = sum(1 for _, e in extracted if e.get("imports_ok"))
    col = sum(1 for _, e in extracted if e.get("collected"))
    repro = sum(1 for _, e in extracted if e.get("reproduces_failure"))
    turns = [e.get("shrunk_turns") for _, e in extracted if e.get("shrunk_turns")]
    pool = sum(1 for c in results.get("candidates", []) if c.get("selected_for_extract"))
    lines.extend(
        [
            "",
            "## Aggregates",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Shrunk failures available | {pool} |",
            f"| Regressions extracted | {n} |",
            f"| Import success rate | {100 * imp / n if n else 0:.1f}% |",
            f"| Collection success rate | {100 * col / n if n else 0:.1f}% |",
            f"| Same-failure reproduction rate | {100 * repro / n if n else 0:.1f}% |",
            f"| Median extracted test user turns | {_med([float(t) for t in turns])} |",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def write_examples_report(cfg: dict, results: dict) -> None:
    out = BENCH / cfg["outputs"]["examples_md"]
    best = None
    best_red = -1.0
    for c in results.get("candidates") or []:
        sh = c.get("shrink") or {}
        if sh.get("shrink_status") != "ok":
            continue
        red = float(sh.get("turn_reduction_pct", 0))
        if red > best_red:
            best_red = red
            best = c
    lines = [
        "# User-simulation regression examples",
        "",
        "## Before / after shrink (one example)",
        "",
    ]
    if best:
        orig = best.get("original_user_turns") or []
        shrunk = best.get("shrink", {}).get("shrunk_user_turns") or []
        lines.append(f"**Failure:** `{best['id']}` ({best['task_id']}, seed {best.get('persona_seed')})")
        lines.append(f"**Turn reduction:** {best['shrink'].get('turn_reduction_pct')}%")
        lines.append("")
        lines.append("### Original user turns")
        lines.append("```text")
        for i, t in enumerate(orig, 1):
            lines.append(f"{i}. {t[:500]}{'...' if len(t) > 500 else ''}")
        lines.append("```")
        lines.append("")
        lines.append("### Shrunk user turns")
        lines.append("```text")
        for i, t in enumerate(shrunk, 1):
            lines.append(f"{i}. {t[:500]}{'...' if len(t) > 500 else ''}")
        lines.append("```")
    else:
        lines.append("_No successful shrink example in this run._")
    lines.extend(["", "## Extracted regression snippet", ""])
    reg_path = BENCH / "tasks" / "regressions" / "extracted_sim_regressions.py"
    if reg_path.exists():
        text = reg_path.read_text(encoding="utf-8")
        if "async def regression_" in text or "async def reg_" in text:
            start = text.find("async def reg")
            if start < 0:
                start = text.find("@ek.scenario")
            snippet = text[start : start + 2500] if start >= 0 else text[-2500:]
            lines.append("```python")
            lines.append(snippet.strip())
            lines.append("```")
        else:
            lines.append("_No extracted regression functions yet._")
    else:
        lines.append("_Regression file not found._")
    lines.extend(
        [
            "",
            "## Optional bug lifecycle (qualitative)",
            "",
            "| Bug | Regression failed before fix | Fix | Shrunk regression passes | Original sim passes |",
            "|-----|------------------------------:|-----|-------------------------:|--------------------:|",
            "| Wrong line after correction (T43) | (document after agent fix) | Use final confirmed line id | — | — |",
            "| Pre-auth disclosure (T45) | (document after agent fix) | Gate sensitive fields | — | — |",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def main() -> None:
    cfg = load_shrink_study_config()
    path = BENCH / cfg["outputs"]["results_json"]
    if not path.exists():
        raise SystemExit(f"missing results: {path}")
    results = json.loads(path.read_text(encoding="utf-8"))
    write_shrink_report(cfg, results)
    write_extraction_report(cfg, results)
    write_examples_report(cfg, results)


if __name__ == "__main__":
    main()
