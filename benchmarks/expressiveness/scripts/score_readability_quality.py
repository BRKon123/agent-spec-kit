#!/usr/bin/env python3
"""LLM-score readability and scenario clarity (A–D) for expressiveness check snippets."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

_EXPR = Path(__file__).resolve().parents[1]
REPO = _EXPR.parents[1]
load_dotenv(REPO / ".env")
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from catalog import SPECIMEN_BY_ID
from scripts.readability_quality_lib import (
    META_PATH,
    RECORDS_PATH,
    build_cells_from_snippets,
    load_canonical_policies,
    merge_existing,
    require_openai_key,
    score_cells,
)
from shared.check_snippets import extract_all_snippets


async def main_async(args: argparse.Namespace) -> int:
    snippets = extract_all_snippets()
    policies = load_canonical_policies()
    cells = build_cells_from_snippets(
        snippets,
        policies=policies,
        specimen_by_id=SPECIMEN_BY_ID,
    )

    existing: dict[str, dict] = {}
    if RECORDS_PATH.is_file() and not args.force_rescore:
        existing = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        cells = merge_existing(cells, existing)

    if args.dry_run:
        print(f"cells={len(cells)}")
        for c in cells[:3]:
            print(c["key"], c["loc"], "lines")
        return 0

    if not args.skip_llm:
        require_openai_key()
        cells = await score_cells(
            cells,
            model=args.model,
            concurrency=args.workers,
            refresh_llm=args.force_rescore,
        )

    out = {c["key"]: c for c in cells}
    if existing and not args.force_rescore:
        out = {**existing, **out}

    RECORDS_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    meta = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "model": args.model,
        "cell_count": len(cells),
        "scored_ok": sum(1 for c in cells if c.get("status") == "ok"),
        "cached": sum(1 for c in cells if c.get("status") == "cached"),
        "llm_errors": sum(1 for c in cells if c.get("status") == "llm_error"),
        "force_rescore": args.force_rescore,
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {RECORDS_PATH} ({meta['scored_ok']} ok, {meta['cached']} cached, {meta['llm_errors']} errors)")
    return 0 if meta["llm_errors"] == 0 else 1


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="openai:gpt-5-mini")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-llm", action="store_true", help="Build cells only; do not call API")
    p.add_argument("--force-rescore", action="store_true", help="Ignore cached assessments")
    args = p.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
