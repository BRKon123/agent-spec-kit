"""Integration: fixture log + mock LLM produces diagnostic_records and table."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from scripts.diagnostic_quality_lib import SpecificityScore, parse_failure_panels
from scripts.extract_diagnostic_quality import build_cells
from scripts.generate_diagnostic_quality_table import generate_table


def test_pipeline_from_fixture_panel(tmp_path: Path):
    log = (Path(__file__).parent / "fixtures" / "sample_failure_panel.log").read_text()
    panels = parse_failure_panels(log)
    assert "test_f02_t29_full" in panels

    results = {
        "F02|T29|F": {
            "fault": "F02",
            "task": "T29",
            "oracle": "F",
            "detected": True,
            "passed": False,
            "scenario": "test_f02_t29_full",
        }
    }
    targets = {"F02": "wrong line_id in tool args"}
    cells = build_cells(results, panels, {}, targets, main_table=True, ceiling=False)
    assert len(cells) == 6

    async def mock_judge(**kwargs):
        return SpecificityScore(specificity_score=4, rationale="fixture ok")

    from scripts.diagnostic_quality_lib import score_cells

    scored = asyncio.run(
        score_cells(cells, model="openai:gpt-5-nano", judge_fn=mock_judge)
    )
    assert all(c.get("status") == "ok" for c in scored)
    out = {c["key"]: c for c in scored}
    md = generate_table(out, {"model": "mock", "scored_ok": 6, "cell_count": 6})
    assert "F02/T29" in md
    assert "agent_spec_kit" in md
