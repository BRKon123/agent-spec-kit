"""Unit tests for TelcoSupportBench-Lite store (no API key)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_BENCH = Path(__file__).resolve().parents[1] / "benchmarks" / "telecom_support"
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from store.tools import make_tools  # noqa: E402


def test_seed_and_permissive_tools() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = TelcoStore(Path(tmp) / "telco.sqlite")
        apply_seed(store, "task_pilot_auth")
        tools = {t.name: t for t in make_tools(store)}
        auth = tools["authenticate_customer"].invoke(
            {"customer_id": "CUST-001", "verification_token": "1985-03-12"}
        )
        assert json.loads(auth)["ok"] is True
        profile = tools["get_customer_profile"].invoke({"customer_id": "CUST-001"})
        assert "Alex" in profile
        credit = tools["apply_bill_credit"].invoke(
            {"customer_id": "CUST-001", "amount": 10.0, "reason": "test"}
        )
        assert json.loads(credit)["ok"] is True
        conn = store.connect()
        try:
            n = conn.execute("SELECT COUNT(*) FROM credits").fetchone()[0]
        finally:
            conn.close()
        assert int(n) == 1


def test_missing_ticket_fault_variant() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = TelcoStore(Path(tmp) / "telco.sqlite")
        apply_seed(store, "task_pilot_auth")
        tools = {t.name: t for t in make_tools(store, variant="fault_missing_ticket")}
        out = tools["create_support_ticket"].invoke(
            {
                "customer_id": "CUST-001",
                "line_id": "LINE-1001",
                "reason": "test",
                "priority": "low",
            }
        )
        assert json.loads(out)["ok"] is True
        conn = store.connect()
        try:
            n = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        finally:
            conn.close()
        assert int(n) == 0
