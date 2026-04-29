"""Regression tests for per-repeat blob path uniqueness."""

from __future__ import annotations

from pathlib import Path

from agent_spec_kit.cli import _write_repeat_blobs
from agent_spec_kit.result_store import LocalResultStore, read_json_blob
from agent_spec_kit.runner import JobResult
from agent_spec_kit.run import ConversationTurn, TurnResult
from agent_spec_kit.storage_records import StorageConfig


def test_write_repeat_blobs_are_unique_per_scenario_repeat_id(tmp_path: Path) -> None:
    """Same run + same repeat_index across scenarios must not overwrite blobs."""
    store = LocalResultStore(StorageConfig(root=tmp_path / ".agent_spec_kit"))

    jr1 = JobResult(
        ok=True,
        scenario_name="s1",
        repeat_index=1,
        turn_results=(ConversationTurn.from_turn("agent", TurnResult(output="alpha")),),
    )
    jr2 = JobResult(
        ok=True,
        scenario_name="s2",
        repeat_index=1,
        turn_results=(ConversationTurn.from_turn("agent", TurnResult(output="beta")),),
    )

    rec1, _ = _write_repeat_blobs(
        store=store,
        run_id="run_x",
        scenario_result_id="run_x_mod.s1_000",
        result=jr1,
    )
    rec2, _ = _write_repeat_blobs(
        store=store,
        run_id="run_x",
        scenario_result_id="run_x_mod.s2_001",
        result=jr2,
    )

    assert rec1.transcript_blob_path is not None
    assert rec2.transcript_blob_path is not None
    assert rec1.transcript_blob_path != rec2.transcript_blob_path

    t1 = read_json_blob(rec1.transcript_blob_path)
    t2 = read_json_blob(rec2.transcript_blob_path)
    assert t1[0]["output"] == "alpha"
    assert t2[0]["output"] == "beta"

