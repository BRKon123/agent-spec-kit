"""Dump / restore TelcoStore rows for diagnostic artifact replay."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from store.seeds import apply_seed
from store.store import TelcoStore

_TABLES = (
    "customers",
    "lines",
    "tickets",
    "credits",
    "sim_orders",
    "appointments",
    "audit_log",
)


def dump_store_state(store: TelcoStore) -> dict[str, Any]:
    conn = store.connect()
    try:
        tables: dict[str, list[dict[str, Any]]] = {}
        for name in _TABLES:
            cur = conn.execute(f"SELECT * FROM {name}")
            tables[name] = [dict(row) for row in cur.fetchall()]
        return {
            "seed": store.seed_meta.get("seed_task") or store.seed_meta.get("seed_name"),
            "seed_meta": dict(store.seed_meta),
            "authenticated_customer_id": store.authenticated_customer_id,
            "fault_first_line_id": store.fault_first_line_id,
            "profile_read_before_auth": store.profile_read_before_auth,
            "fault_network_events_pulled": store.fault_network_events_pulled,
            "tables": tables,
        }
    finally:
        conn.close()


def write_store_snapshot(store: TelcoStore, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dump_store_state(store)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def load_store_from_snapshot(snapshot: dict[str, Any]) -> TelcoStore:
    base = Path(tempfile.mkdtemp(prefix="telco_diag_"))
    telco = TelcoStore(base / "telco.sqlite")
    seed_name = snapshot.get("seed") or snapshot.get("seed_meta", {}).get("seed_name")
    if seed_name:
        apply_seed(telco, str(seed_name))
    meta = snapshot.get("seed_meta") or {}
    if meta:
        telco.seed_meta.update(meta)
    telco.authenticated_customer_id = snapshot.get("authenticated_customer_id")
    telco.fault_first_line_id = snapshot.get("fault_first_line_id")
    telco.profile_read_before_auth = bool(snapshot.get("profile_read_before_auth"))
    telco.fault_network_events_pulled = bool(snapshot.get("fault_network_events_pulled"))
    tables = snapshot.get("tables") or {}
    conn = telco.connect()
    try:
        for table, rows in tables.items():
            if table not in _TABLES or not rows:
                continue
            cols = list(rows[0].keys())
            placeholders = ",".join("?" * len(cols))
            col_sql = ",".join(cols)
            for row in rows:
                conn.execute(
                    f"INSERT OR REPLACE INTO {table} ({col_sql}) VALUES ({placeholders})",
                    tuple(row[c] for c in cols),
                )
        conn.commit()
    finally:
        conn.close()
    return telco


def cleanup_store(store: TelcoStore) -> None:
    shutil.rmtree(store.db_path.parent, ignore_errors=True)
