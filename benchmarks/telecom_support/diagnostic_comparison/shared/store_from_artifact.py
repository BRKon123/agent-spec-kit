"""Load TelcoStore from exported diagnostic artifacts (no check semantics)."""

from __future__ import annotations

from typing import Any

from store.snapshot import cleanup_store, load_store_from_snapshot


def load_store(artifact: dict[str, Any]):
    snapshot = artifact.get("store_snapshot")
    if not snapshot:
        raise ValueError("artifact missing store_snapshot")
    return load_store_from_snapshot(snapshot)


def with_store(artifact: dict[str, Any], fn):
    store = load_store(artifact)
    try:
        return fn(store)
    finally:
        cleanup_store(store)
