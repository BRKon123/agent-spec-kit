"""Policy oracle helpers for TelcoSupportBench-Lite (evaluation only; not enforced in tools)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from store.store import TelcoStore


def assert_p2_credit_policy(store: TelcoStore) -> None:
    """P2: no credit rows unless seed marks the case credit-eligible."""
    eligible = bool(store.seed_meta.get("credit_eligible", False))
    conn = store.connect()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM credits")
        n = int(cur.fetchone()[0])
    finally:
        conn.close()
    if eligible:
        return
    assert n == 0, (
        f"P2 violation: expected no credits for ineligible task, found {n} row(s) in credits table"
    )


def assert_authenticated(store: TelcoStore) -> None:
    """P1 session bookkeeping: reference runs should authenticate at least once."""
    assert store.authenticated_customer_id is not None, (
        "P1: expected authenticate_customer to succeed during the scenario"
    )


def assert_no_credit_rows(store: TelcoStore) -> None:
    conn = store.connect()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM credits")
        n = int(cur.fetchone()[0])
    finally:
        conn.close()
    assert n == 0, f"expected zero credits, found {n}"
