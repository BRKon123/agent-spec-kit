"""Load JSON seed bundles into a TelcoStore."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from store.store import TelcoStore

_SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"

# FK-safe insert order
_TABLE_ORDER = (
    "customers",
    "plans",
    "lines",
    "devices",
    "usage_events",
    "network_outages",
    "network_events",
    "billing_events",
    "diagnostics",
    "tickets",
    "credits",
    "appointments",
    "sim_orders",
    "audit_log",
)


def seed_path(task_id: str) -> Path:
    return _SEEDS_DIR / f"{task_id}.json"


def load_seed_dict(task_id: str) -> dict[str, Any]:
    path = seed_path(task_id)
    if not path.exists():
        raise FileNotFoundError(f"no seed file for task_id={task_id!r}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def apply_seed(store: TelcoStore, task_id: str | dict[str, Any]) -> dict[str, Any]:
    """Insert seed rows; reset session auth. Returns seed meta (e.g. policy hints for oracles)."""
    data = load_seed_dict(task_id) if isinstance(task_id, str) else task_id
    store.authenticated_customer_id = None
    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    store.seed_meta = dict(meta)

    conn = store.connect()
    try:
        for table in _TABLE_ORDER:
            rows = data.get(table, [])
            if not rows:
                continue
            for row in rows:
                cols = ", ".join(row.keys())
                placeholders = ", ".join("?" for _ in row)
                conn.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                    tuple(row.values()),
                )
        conn.commit()
    finally:
        conn.close()
    return store.seed_meta


def list_seed_task_ids() -> list[str]:
    return sorted(p.stem for p in _SEEDS_DIR.glob("*.json"))
