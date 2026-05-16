"""TelcoSupportBench-Lite SQLite store (one file per scenario job)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class TelcoStore:
    """Mutable telco support database; permissive tools close over one instance per run."""

    __slots__ = (
        "db_path",
        "authenticated_customer_id",
        "seed_meta",
        "_ticket_seq",
        "_sim_order_seq",
    )

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.authenticated_customer_id: str | None = None
        self.seed_meta: dict[str, Any] = {}
        self._ticket_seq = 0
        self._sim_order_seq = 0
        conn = self.connect()
        try:
            conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def next_ticket_id(self) -> str:
        self._ticket_seq += 1
        return f"TCK-{self._ticket_seq:05d}"

    def next_sim_order_id(self) -> str:
        self._sim_order_seq += 1
        return f"SIM-{self._sim_order_seq:05d}"

    def row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {k: row[k] for k in row.keys()}

    def audit(self, conn: sqlite3.Connection, *, customer_id: str | None, action: str, detail: str) -> None:
        from datetime import UTC, datetime

        conn.execute(
            "INSERT INTO audit_log (customer_id, action, detail, created_at) VALUES (?,?,?,?)",
            (customer_id, action, detail, datetime.now(UTC).isoformat()),
        )

    def parse_settings(self, raw: str) -> dict[str, Any]:
        try:
            val = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return val if isinstance(val, dict) else {}

    def dump_settings(self, obj: dict[str, Any]) -> str:
        return json.dumps(obj, sort_keys=True)
