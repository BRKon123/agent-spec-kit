"""Tests for `agent-spec-kit clear` (deletes the local result store)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from agent_spec_kit.cli import _run_clear, main


@pytest.fixture
def cwd_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Chdir into ``tmp_path`` so ``StorageConfig().root`` resolves there."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _seed_store(root: Path) -> None:
    (root / "blobs").mkdir(parents=True, exist_ok=True)
    (root / "results.sqlite").write_bytes(b"x")
    (root / "blobs" / "marker.txt").write_text("y")


def test_run_clear_skips_prompt_with_yes_flag(cwd_tmp: Path) -> None:
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)

    def explode(_prompt: str) -> str:
        raise AssertionError("input() must not be called when --yes is passed")

    rc = _run_clear(skip_prompt=True, input_fn=explode)
    assert rc == 0
    assert not root.exists()


def test_run_clear_yes_typed_at_prompt_deletes(cwd_tmp: Path) -> None:
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)
    rc = _run_clear(skip_prompt=False, input_fn=lambda _p: "yes")
    assert rc == 0
    assert not root.exists()


def test_run_clear_yes_is_case_insensitive_and_strips_whitespace(cwd_tmp: Path) -> None:
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)
    rc = _run_clear(skip_prompt=False, input_fn=lambda _p: "  YES \n")
    assert rc == 0
    assert not root.exists()


@pytest.mark.parametrize("answer", ["", "y", "no", "yeah", "yess", "1"])
def test_run_clear_anything_other_than_yes_aborts(cwd_tmp: Path, answer: str) -> None:
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)
    rc = _run_clear(skip_prompt=False, input_fn=lambda _p: answer)
    assert rc == 1
    # Store must still be on disk.
    assert (root / "results.sqlite").exists()
    assert (root / "blobs" / "marker.txt").exists()


def test_run_clear_eof_at_prompt_aborts(cwd_tmp: Path) -> None:
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)

    def raise_eof(_prompt: str) -> str:
        raise EOFError

    rc = _run_clear(skip_prompt=False, input_fn=raise_eof)
    assert rc == 1
    assert (root / "results.sqlite").exists()


def test_run_clear_noop_when_store_does_not_exist(cwd_tmp: Path) -> None:
    """No directory => no-op, returns 0, doesn't prompt."""
    assert not (cwd_tmp / ".agent_spec_kit").exists()

    def explode(_prompt: str) -> str:
        raise AssertionError("input() must not be called when nothing to delete")

    rc = _run_clear(skip_prompt=False, input_fn=explode)
    assert rc == 0


def test_main_clear_with_yes_flag(cwd_tmp: Path) -> None:
    """End-to-end: argparse `clear --yes` invokes _run_clear with skip_prompt=True."""
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)
    rc = main(["clear", "--yes"])
    assert rc == 0
    assert not root.exists()


def test_main_clear_short_yes_flag(cwd_tmp: Path) -> None:
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)
    rc = main(["clear", "-y"])
    assert rc == 0
    assert not root.exists()


def test_main_clear_interactive_no_via_stdin(
    cwd_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`main(["clear"])` without --yes reads stdin; non-yes input aborts."""
    root = cwd_tmp / ".agent_spec_kit"
    _seed_store(root)
    monkeypatch.setattr("sys.stdin", io.StringIO("no\n"))
    rc = main(["clear"])
    assert rc == 1
    assert (root / "results.sqlite").exists()
