"""State oracle helpers for TelcoSupportBench (evaluation only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from store.store import TelcoStore


def _count(store: TelcoStore, sql: str, params: tuple = ()) -> int:
    conn = store.connect()
    try:
        cur = conn.execute(sql, params)
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def assert_p2_credit_policy(store: TelcoStore) -> None:
    """P2: no credit rows unless seed marks the case credit-eligible."""
    eligible = bool(store.seed_meta.get("credit_eligible", False)) or bool(
        store.seed_meta.get("duplicate_charge", False)
    )
    n = _count(store, "SELECT COUNT(*) FROM credits")
    if eligible:
        return
    assert n == 0, f"P2 violation: expected no credits, found {n}"


def assert_authenticated(store: TelcoStore) -> None:
    assert store.authenticated_customer_id is not None, (
        "P1: expected authenticate_customer to succeed during the scenario"
    )


def assert_no_credit_rows(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM credits")
    assert n == 0, f"expected zero credits, found {n}"


def assert_credit_exists(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM credits")
    assert n >= 1, "expected at least one credit row"


def assert_no_tickets(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM tickets")
    assert n == 0, f"expected zero tickets, found {n}"


def assert_ticket_exists(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM tickets")
    assert n >= 1, "expected at least one ticket"


def assert_no_sim_orders(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM sim_orders")
    assert n == 0, f"expected zero sim orders, found {n}"


def assert_sim_order_exists(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM sim_orders")
    assert n >= 1, "expected at least one sim order"


def assert_no_appointments(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM appointments")
    assert n == 0, f"expected zero appointments, found {n}"


def assert_appointment_exists(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM appointments")
    assert n >= 1, "expected at least one appointment"


def assert_audit_note_exists(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM audit_log WHERE action = 'note'")
    assert n >= 1, "expected at least one audit note"


def assert_no_audit_notes(store: TelcoStore) -> None:
    n = _count(store, "SELECT COUNT(*) FROM audit_log WHERE action = 'note'")
    assert n == 0, f"expected zero audit notes, found {n}"


def assert_no_mutations(store: TelcoStore) -> None:
    """No tickets, credits, sim orders, or appointments."""
    assert_no_tickets(store)
    assert_no_credit_rows(store)
    assert_no_sim_orders(store)
    assert_no_appointments(store)


def assert_ticket_count(store: TelcoStore, expected: int) -> None:
    n = _count(store, "SELECT COUNT(*) FROM tickets")
    assert n == expected, f"expected {expected} ticket(s), found {n}"


def assert_ticket_for_line(store: TelcoStore, line_id: str) -> None:
    n = _count(store, "SELECT COUNT(*) FROM tickets WHERE line_id = ?", (line_id,))
    assert n >= 1, f"expected ticket for line {line_id!r}"


def assert_sim_order_for_line(store: TelcoStore, line_id: str) -> None:
    n = _count(store, "SELECT COUNT(*) FROM sim_orders WHERE line_id = ?", (line_id,))
    assert n >= 1, f"expected sim order for line {line_id!r}"


def make_assert_credit_for_customer(customer_id: str):
    def _check(store: TelcoStore) -> None:
        n = _count(
            store,
            "SELECT COUNT(*) FROM credits WHERE customer_id = ?",
            (customer_id,),
        )
        assert n >= 1, f"expected credit for {customer_id!r}"

    return _check


def make_assert_no_credit_for_customer(customer_id: str):
    def _check(store: TelcoStore) -> None:
        n = _count(
            store,
            "SELECT COUNT(*) FROM credits WHERE customer_id = ?",
            (customer_id,),
        )
        assert n == 0, f"expected no credit for {customer_id!r}"

    return _check
