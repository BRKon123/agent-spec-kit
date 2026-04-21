"""Rich CLI reporter smoke (captured stream)."""

from __future__ import annotations

import io

from agent_spec_kit.cli_reporting import emit_failure_detail, emit_job_compact, emit_summary_table
from agent_spec_kit.failures import Counterexample
from agent_spec_kit.runner import JobResult


def test_emit_summary_table_contains_rows() -> None:
    buf = io.StringIO()
    ok = JobResult(
        ok=True,
        scenario_name="t_ok",
        repeat_index=1,
        repeat_total=1,
        detail=None,
        duration_s=0.01,
        counterexample=None,
    )
    bad = JobResult(
        ok=False,
        scenario_name="t_bad",
        repeat_index=1,
        repeat_total=1,
        detail="boom",
        duration_s=0.02,
        counterexample=Counterexample(
            headline="t_bad: boom",
            location="step 0, turn 0",
            path="$[0]",
            expected_summary="x",
            actual_min="y",
            notes=(),
        ),
    )
    emit_summary_table([ok, bad], file=buf)
    text = buf.getvalue()
    assert "t_ok" in text and "t_bad" in text
    assert "1 passed" in text and "1 failed" in text


def test_emit_summary_table_wraps_long_test_name() -> None:
    """Test column uses fold + max_width; very long names are capped like failure text."""
    buf = io.StringIO()
    long_wrapped = "word_one " * 12 + "tail"  # > 56 chars, spaces so Rich can fold
    emit_summary_table(
        [
            JobResult(
                ok=True,
                scenario_name=long_wrapped.strip(),
                repeat_index=1,
                repeat_total=1,
                detail=None,
                duration_s=0.0,
                counterexample=None,
            )
        ],
        file=buf,
    )
    text = buf.getvalue()
    assert "word_one" in text and "tail" in text

    buf2 = io.StringIO()
    huge = "x" * 250
    emit_summary_table(
        [
            JobResult(
                ok=True,
                scenario_name=huge,
                repeat_index=1,
                repeat_total=1,
                detail=None,
                duration_s=0.0,
                counterexample=None,
            )
        ],
        file=buf2,
    )
    out2 = buf2.getvalue()
    assert "..." in out2
    assert huge not in out2


def test_emit_failure_detail_omits_root_dollar_path() -> None:
    buf = io.StringIO()
    r = JobResult(
        ok=False,
        scenario_name="t",
        repeat_index=1,
        repeat_total=1,
        detail="x",
        duration_s=1.0,
        counterexample=Counterexample(
            headline="h",
            location="step 1, turn 0",
            path="$",
            expected_summary="e",
            actual_min="[]",
            notes=(),
        ),
    )
    emit_failure_detail(r, file=buf)
    assert "Path:" not in buf.getvalue()


def test_emit_failure_detail_shows_non_root_path() -> None:
    buf = io.StringIO()
    r = JobResult(
        ok=False,
        scenario_name="t",
        repeat_index=1,
        repeat_total=1,
        detail="x",
        duration_s=1.0,
        counterexample=Counterexample(
            headline="h",
            location="step 0, turn 0",
            path="$[0].name",
            expected_summary="e",
            actual_min="y",
            notes=(),
        ),
    )
    emit_failure_detail(r, file=buf)
    assert "Path: $[0].name" in buf.getvalue()
    assert "Actual:" in buf.getvalue()
    assert "witness" not in buf.getvalue().lower()


def test_emit_job_compact_still_works() -> None:
    buf = io.StringIO()
    emit_job_compact(
        JobResult(
            ok=True,
            scenario_name="x",
            repeat_index=1,
            repeat_total=1,
            detail=None,
            duration_s=0.0,
            counterexample=None,
        ),
        file=buf,
    )
    assert "PASS" in buf.getvalue() and "x" in buf.getvalue()
