"""Simulate DB mutations for state-check specimens (scripted agent does not write SQLite)."""

from __future__ import annotations

from store.store import TelcoStore


def insert_ticket(store: TelcoStore, *, line_id: str, ticket_id: str = "INC-9001") -> None:
    meta = store.seed_meta
    cid = str(meta.get("customer_id", "CUST-001"))
    conn = store.connect()
    try:
        conn.execute(
            "INSERT INTO tickets (ticket_id, customer_id, line_id, reason, priority, status, created_at) "
            "VALUES (?,?,?,?,?,?,datetime('now'))",
            (ticket_id, cid, line_id, "expressiveness specimen", "normal", "open"),
        )
        conn.commit()
    finally:
        conn.close()
