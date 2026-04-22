"""Rich CLI reporter smoke (captured stream)."""

from __future__ import annotations

import io

from agent_spec_kit.cli_reporting import emit_failure_detail, emit_job_compact, emit_summary_table
from agent_spec_kit.events import AgentTurnEvent, ToolCallEvent
from agent_spec_kit.failures import Counterexample
from agent_spec_kit.runner import JobResult


def test_emit_summary_table_failure_column_short_check_kind() -> None:
    """Failure column shows check_kind, not the long detail headline."""
    buf = io.StringIO()
    bad = JobResult(
        ok=False,
        scenario_name="t_fail",
        repeat_index=1,
        repeat_total=1,
        detail="assert_output: t_fail: value does not equal expected",
        duration_s=0.01,
        counterexample=Counterexample(
            headline="long",
            location="step 1, turn 0",
            path=None,
            expected_summary="e",
            actual_min="a",
            notes=(),
            check_kind="assert_output",
        ),
    )
    emit_summary_table([bad], file=buf)
    text = buf.getvalue()
    assert "assert_output" in text
    assert "value does not equal" not in text


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
    out = buf.getvalue()
    assert "Path: $[0].name" in out
    assert "Actual:" in out
    assert "Where:" in out
    assert "witness" not in out.lower()


def test_emit_failure_detail_includes_check_kind_and_event_trace() -> None:
    root = AgentTurnEvent(user_input="hi", agent_output="out", turn_index=0)
    root.children.append(ToolCallEvent(tool_name="demo_tool", args={"k": 1}, result=2))
    buf = io.StringIO()
    emit_failure_detail(
        JobResult(
            ok=False,
            scenario_name="t_trace",
            repeat_index=1,
            repeat_total=1,
            detail="d",
            duration_s=0.1,
            counterexample=Counterexample(
                headline="h",
                location="step 1, turn 0",
                path=None,
                expected_summary="exp",
                actual_min="act",
                notes=(),
                check_kind="assert_tool_calls",
                location_detail="Queued step 1 — assert_tool_calls — after user message #1",
                events=(root,),
            ),
        ),
        file=buf,
    )
    text = buf.getvalue()
    assert "Check: assert_tool_calls" in text
    assert "Where:" in text
    assert "Event trace (till failure)" in text
    assert "demo_tool" in text
    assert "Hint:" not in text


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


def test_emit_summary_table_includes_param_columns() -> None:
    """One column per @parametrize axis; values use Case id when name is absent."""
    buf = io.StringIO()
    emit_summary_table(
        [
            JobResult(
                ok=True,
                scenario_name="s",
                case_id="llm_model=fast+task=a",
                repeat_index=1,
                repeat_total=1,
                detail=None,
                duration_s=0.0,
                counterexample=None,
                param_cells={"llm_model": "fast", "task": "A task"},
            ),
            JobResult(
                ok=True,
                scenario_name="s",
                case_id="llm_model=slow+task=b",
                repeat_index=1,
                repeat_total=1,
                detail=None,
                duration_s=0.0,
                counterexample=None,
                param_cells={"llm_model": "slow", "task": "B thing"},
            ),
        ],
        file=buf,
    )
    out = buf.getvalue()
    assert "llm_model" in out and "task" in out
    assert "fast" in out and "slow" in out
    assert "A task" in out
    # First column is scenario name, not the composite ``[case_id]`` suffix.
    assert "llm_model=fast" not in out
