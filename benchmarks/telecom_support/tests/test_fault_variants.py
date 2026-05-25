"""Unit tests for fault variant tool-line helpers."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from store.fault_variants import decoy_line_id, resolve_mutation_line  # noqa: E402
from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402


def test_fault_wrong_line_rewrites_seed_line():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T29")
    seed = store.seed_meta["line_id"]
    out = resolve_mutation_line(store, "fault_wrong_line", seed)
    assert out == decoy_line_id(store)
    assert out != seed


def test_fault_stale_belief_sticks_to_first_line():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T46")
    first = resolve_mutation_line(store, "fault_stale_belief", "LINE-WRONG")
    second = resolve_mutation_line(store, "fault_stale_belief", store.seed_meta["line_id"])
    assert first == second == "LINE-WRONG"


def test_reference_variant_no_rewrite():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T29")
    seed = store.seed_meta["line_id"]
    assert resolve_mutation_line(store, "reference", seed) == seed
