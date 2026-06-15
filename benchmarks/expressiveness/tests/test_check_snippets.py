"""Tests for CHECK block extraction and LOC parity."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from catalog import SPECIMENS
from shared.check_snippets import FRAMEWORKS, extract_all_snippets, loc_by_framework

SCRIPT = _EXPR / "scripts" / "count_check_loc.py"


def test_extract_all_snippets_count():
    snippets = extract_all_snippets()
    assert len(snippets) == 12 * len(FRAMEWORKS)
    keys = {(s.check_id, s.framework) for s in snippets}
    assert len(keys) == len(snippets)


def test_loc_parity_with_count_script():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(_EXPR),
    )
    expected: dict[str, dict[str, int]] = {}
    current: str | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            expected[current] = {}
        elif current and line.strip().startswith("C"):
            cid, _, n = line.strip().partition(":")
            expected[current][cid] = int(n.strip())

    actual = loc_by_framework()
    assert actual == expected


def test_every_specimen_framework_has_snippet():
    snippets = extract_all_snippets()
    by_key = {(s.check_id, s.framework): s for s in snippets}
    for spec in SPECIMENS:
        for fw in FRAMEWORKS:
            snip = by_key[(spec.check_id, fw)]
            assert snip.snippet_text.strip()
            assert snip.loc > 0
